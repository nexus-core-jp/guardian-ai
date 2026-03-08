"""アラートエスカレーションサービス"""

import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertType, AlertSeverity
from app.services.anomaly_detector import AnomalyResult
from app.services.notification import NotificationService


# アラート種別ごとの日本語タイトル
ALERT_TITLES = {
    AlertType.ROUTE_DEVIATION: "ルート逸脱",
    AlertType.SPEED_ANOMALY: "速度異常",
    AlertType.ZONE_ENTRY: "危険エリア侵入",
    AlertType.SOS: "SOS",
    AlertType.BATTERY_LOW: "バッテリー低下",
    AlertType.DEVICE_OFFLINE: "デバイスオフライン",
    AlertType.GEOFENCE_EXIT: "ジオフェンス外出",
    AlertType.ARRIVAL: "到着通知",
    AlertType.DEPARTURE: "出発通知",
}

# 重要度ごとのエスカレーション時間（秒）
ESCALATION_RULES = {
    AlertSeverity.INFO: {
        "next_severity": AlertSeverity.WARNING,
        "escalation_after_seconds": 1800,  # 30分
    },
    AlertSeverity.WARNING: {
        "next_severity": AlertSeverity.CRITICAL,
        "escalation_after_seconds": 600,  # 10分
    },
    AlertSeverity.CRITICAL: {
        "next_severity": AlertSeverity.EMERGENCY,
        "escalation_after_seconds": 300,  # 5分
    },
}


class AlertService:
    """
    アラートサービス
    アラートの作成、エスカレーション、解決を管理する。

    エスカレーションフロー:
    info → warning → critical → emergency

    自動エスカレーション:
    - 未対応のアラートは時間経過で自動的にエスカレーションされる
    - 重要度が上がるごとに通知頻度が上がる
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.notification_service = NotificationService()

    async def create_alert(
        self,
        child_id: uuid.UUID,
        user_id: uuid.UUID,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> Alert:
        """アラートを作成する"""
        # 同じ種別の未解決アラートがないか確認（重複防止）
        existing = await self.db.execute(
            select(Alert).where(
                Alert.child_id == child_id,
                Alert.alert_type == alert_type,
                Alert.is_resolved == False,
            ).order_by(desc(Alert.created_at)).limit(1)
        )
        existing_alert = existing.scalar_one_or_none()

        if existing_alert:
            # 5分以内の同じアラートは重複として無視
            time_diff = (
                datetime.now(timezone.utc)
                - existing_alert.created_at.replace(tzinfo=timezone.utc)
            ).total_seconds()
            if time_diff < 300:
                return existing_alert

        alert = Alert(
            child_id=child_id,
            user_id=user_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            latitude=latitude,
            longitude=longitude,
        )
        self.db.add(alert)
        await self.db.flush()

        # プッシュ通知を送信
        try:
            await self.notification_service.send_alert_notification(
                user_id=user_id,
                alert=alert,
                db=self.db,
            )
        except Exception:
            pass  # 通知送信失敗はアラート作成に影響させない

        return alert

    async def create_alert_from_anomaly(
        self,
        child_id: uuid.UUID,
        user_id: uuid.UUID,
        anomaly: AnomalyResult,
        latitude: float,
        longitude: float,
    ) -> Alert:
        """異常検知結果からアラートを作成する"""
        alert_type = anomaly.anomaly_type or AlertType.ROUTE_DEVIATION
        title = ALERT_TITLES.get(
            AlertType(alert_type) if isinstance(alert_type, str) else alert_type,
            "異常検知",
        )

        return await self.create_alert(
            child_id=child_id,
            user_id=user_id,
            alert_type=alert_type,
            severity=anomaly.severity,
            title=title,
            message=anomaly.message,
            latitude=latitude,
            longitude=longitude,
        )

    async def escalate_alert(self, alert_id: uuid.UUID) -> Alert | None:
        """アラートをエスカレーションする"""
        result = await self.db.execute(
            select(Alert).where(Alert.id == alert_id, Alert.is_resolved == False)
        )
        alert = result.scalar_one_or_none()

        if alert is None:
            return None

        current_severity = AlertSeverity(alert.severity)
        rule = ESCALATION_RULES.get(current_severity)

        if rule is None:
            # すでに最高レベル
            return alert

        alert.severity = rule["next_severity"]
        await self.db.flush()

        # エスカレーション通知を送信
        try:
            await self.notification_service.send_escalation_notification(
                user_id=alert.user_id,
                alert=alert,
                db=self.db,
            )
        except Exception:
            pass

        return alert

    async def check_and_escalate(self) -> list[Alert]:
        """
        未解決アラートのエスカレーションチェックを実行する。
        定期バッチジョブから呼び出される。
        """
        escalated = []

        for severity, rule in ESCALATION_RULES.items():
            threshold_time = datetime.now(timezone.utc) - timedelta(
                seconds=rule["escalation_after_seconds"]
            )

            result = await self.db.execute(
                select(Alert).where(
                    Alert.severity == severity,
                    Alert.is_resolved == False,
                    Alert.is_read == False,
                    Alert.created_at < threshold_time,
                )
            )
            alerts_to_escalate = result.scalars().all()

            for alert in alerts_to_escalate:
                escalated_alert = await self.escalate_alert(alert.id)
                if escalated_alert:
                    escalated.append(escalated_alert)

        return escalated

    async def resolve_alert(self, alert_id: uuid.UUID) -> Alert | None:
        """アラートを解決済みにする"""
        result = await self.db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if alert is None:
            return None

        alert.is_resolved = True
        alert.resolved_at = datetime.now(timezone.utc)
        await self.db.flush()

        return alert

    async def get_active_alerts_count(self, user_id: uuid.UUID) -> dict:
        """ユーザーのアクティブアラート統計を取得する"""
        result = await self.db.execute(
            select(
                Alert.severity,
                func.count(Alert.id),
            )
            .where(
                Alert.user_id == user_id,
                Alert.is_resolved == False,
            )
            .group_by(Alert.severity)
        )
        counts = {row[0]: row[1] for row in result.all()}

        return {
            "total": sum(counts.values()),
            "info": counts.get(AlertSeverity.INFO, 0),
            "warning": counts.get(AlertSeverity.WARNING, 0),
            "critical": counts.get(AlertSeverity.CRITICAL, 0),
            "emergency": counts.get(AlertSeverity.EMERGENCY, 0),
        }

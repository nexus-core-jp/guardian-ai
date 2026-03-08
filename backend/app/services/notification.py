"""プッシュ通知サービス (Firebase Cloud Messaging)"""

import uuid
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.models.alert import Alert, AlertSeverity

settings = get_settings()
logger = logging.getLogger(__name__)

# FCMの初期化（credentials設定済みの場合のみ）
_fcm_initialized = False

try:
    if settings.FCM_CREDENTIALS_PATH and Path(settings.FCM_CREDENTIALS_PATH).exists():
        import firebase_admin
        from firebase_admin import credentials, messaging

        cred = credentials.Certificate(settings.FCM_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
        _fcm_initialized = True
        logger.info("Firebase Cloud Messaging 初期化完了")
except Exception as e:
    logger.warning(f"FCM初期化スキップ（本番環境では設定が必要です）: {e}")


# 重要度ごとの通知設定
NOTIFICATION_CONFIG = {
    AlertSeverity.INFO: {
        "sound": "default",
        "priority": "normal",
        "channel_id": "guardian_info",
    },
    AlertSeverity.WARNING: {
        "sound": "warning.wav",
        "priority": "high",
        "channel_id": "guardian_warning",
    },
    AlertSeverity.CRITICAL: {
        "sound": "critical.wav",
        "priority": "high",
        "channel_id": "guardian_critical",
    },
    AlertSeverity.EMERGENCY: {
        "sound": "emergency.wav",
        "priority": "high",
        "channel_id": "guardian_emergency",
    },
}


class NotificationService:
    """
    プッシュ通知サービス
    Firebase Cloud Messagingを使用して保護者にプッシュ通知を送信する。
    """

    async def send_push(
        self,
        user_id: uuid.UUID,
        title: str,
        body: str,
        data: dict | None = None,
        db: AsyncSession | None = None,
    ) -> bool:
        """
        プッシュ通知を送信する。

        Args:
            user_id: 送信先ユーザーID
            title: 通知タイトル
            body: 通知本文
            data: 追加データ
            db: DBセッション

        Returns:
            送信成功かどうか
        """
        if not _fcm_initialized:
            logger.debug(f"FCM未設定のため通知をスキップ: {title}")
            return False

        if db is None:
            logger.warning("DBセッションが未提供です")
            return False

        # ユーザーのFCMトークンを取得
        result = await db.execute(
            select(User.fcm_token).where(User.id == user_id)
        )
        fcm_token = result.scalar_one_or_none()

        if not fcm_token:
            logger.debug(f"FCMトークン未設定のユーザー: {user_id}")
            return False

        try:
            from firebase_admin import messaging

            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data={k: str(v) for k, v in (data or {}).items()},
                token=fcm_token,
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        sound="default",
                        click_action="OPEN_ALERT",
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            badge=1,
                            content_available=True,
                        ),
                    ),
                ),
            )

            response = messaging.send(message)
            logger.info(f"通知送信成功: {response}")
            return True

        except Exception as e:
            logger.error(f"通知送信失敗: {e}")
            return False

    async def send_alert_notification(
        self,
        user_id: uuid.UUID,
        alert: Alert,
        db: AsyncSession,
    ) -> bool:
        """アラート通知を送信する"""
        severity = AlertSeverity(alert.severity)
        config = NOTIFICATION_CONFIG.get(severity, NOTIFICATION_CONFIG[AlertSeverity.INFO])

        # 重要度に応じたプレフィックス
        prefix_map = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
            AlertSeverity.EMERGENCY: "🆘",
        }
        prefix = prefix_map.get(severity, "")

        title = f"{prefix} {alert.title}"
        body = alert.message or "詳細を確認してください"

        data = {
            "alert_id": str(alert.id),
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "child_id": str(alert.child_id),
            "channel_id": config["channel_id"],
        }

        if alert.latitude and alert.longitude:
            data["latitude"] = str(alert.latitude)
            data["longitude"] = str(alert.longitude)

        return await self.send_push(
            user_id=user_id,
            title=title,
            body=body,
            data=data,
            db=db,
        )

    async def send_escalation_notification(
        self,
        user_id: uuid.UUID,
        alert: Alert,
        db: AsyncSession,
    ) -> bool:
        """エスカレーション通知を送信する"""
        severity = AlertSeverity(alert.severity)

        severity_names = {
            AlertSeverity.WARNING: "警告",
            AlertSeverity.CRITICAL: "重大",
            AlertSeverity.EMERGENCY: "緊急",
        }
        severity_name = severity_names.get(severity, "通知")

        title = f"🔺 アラートエスカレーション: {severity_name}"
        body = f"「{alert.title}」が{severity_name}レベルにエスカレーションされました。\n{alert.message or ''}"

        return await self.send_push(
            user_id=user_id,
            title=title,
            body=body,
            data={
                "alert_id": str(alert.id),
                "type": "escalation",
                "severity": alert.severity,
            },
            db=db,
        )

    async def send_arrival_notification(
        self,
        user_id: uuid.UUID,
        child_name: str,
        destination_name: str,
        db: AsyncSession,
    ) -> bool:
        """到着通知を送信する"""
        return await self.send_push(
            user_id=user_id,
            title="✅ 到着通知",
            body=f"{child_name}さんが{destination_name}に到着しました。",
            data={"type": "arrival"},
            db=db,
        )

    async def send_departure_notification(
        self,
        user_id: uuid.UUID,
        child_name: str,
        origin_name: str,
        db: AsyncSession,
    ) -> bool:
        """出発通知を送信する"""
        return await self.send_push(
            user_id=user_id,
            title="🚶 出発通知",
            body=f"{child_name}さんが{origin_name}を出発しました。",
            data={"type": "departure"},
            db=db,
        )

"""行動異常検知サービス"""

import uuid
import math
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.models.route import Route
from app.models.alert import AlertType, AlertSeverity


@dataclass
class AnomalyResult:
    """異常検知結果"""
    is_anomalous: bool
    anomaly_type: str | None = None
    severity: str = "info"
    confidence: float = 0.0
    message: str = ""
    details: dict | None = None


class AnomalyDetector:
    """
    行動異常検知サービス
    子どもの位置情報パターンを分析し、異常な行動を検知する。

    検知項目:
    - ルート逸脱: 推奨ルートから大きく外れた場合
    - 速度異常: 歩行ではありえない速度（車に乗せられた可能性）
    - 異常な停止: 予期しない場所での長時間停止
    - 時間異常: 通常の行動時間外の移動
    """

    # 小学生の歩行速度範囲 (m/s)
    NORMAL_WALKING_SPEED_MIN = 0.5   # 0.5 m/s ≈ 1.8 km/h
    NORMAL_WALKING_SPEED_MAX = 2.0   # 2.0 m/s ≈ 7.2 km/h
    RUNNING_SPEED_MAX = 4.0          # 4.0 m/s ≈ 14.4 km/h

    # 車両速度の閾値 (m/s)
    VEHICLE_SPEED_THRESHOLD = 8.0    # 8.0 m/s ≈ 28.8 km/h

    # ルート逸脱の閾値（メートル）
    ROUTE_DEVIATION_WARNING = 200    # 200m: 警告
    ROUTE_DEVIATION_CRITICAL = 500   # 500m: 重大

    # 停止検知の閾値
    STOP_SPEED_THRESHOLD = 0.3       # 0.3 m/s 以下は停止とみなす
    STOP_DURATION_WARNING = 600      # 10分: 警告
    STOP_DURATION_CRITICAL = 1800    # 30分: 重大

    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_anomaly(
        self,
        child_id: uuid.UUID,
        latitude: float,
        longitude: float,
        speed: float | None = None,
    ) -> AnomalyResult:
        """
        現在の位置情報に基づいて異常を検知する。

        Args:
            child_id: 子どものID
            latitude: 現在の緯度
            longitude: 現在の経度
            speed: 現在の速度 (m/s)

        Returns:
            異常検知結果
        """
        anomalies: list[AnomalyResult] = []

        # 1. 速度異常チェック
        if speed is not None:
            speed_anomaly = self._check_speed_anomaly(speed)
            if speed_anomaly.is_anomalous:
                anomalies.append(speed_anomaly)

        # 2. ルート逸脱チェック
        route_anomaly = await self._check_route_deviation(
            child_id, latitude, longitude
        )
        if route_anomaly.is_anomalous:
            anomalies.append(route_anomaly)

        # 3. 異常停止チェック
        stop_anomaly = await self._check_unusual_stop(
            child_id, latitude, longitude, speed
        )
        if stop_anomaly.is_anomalous:
            anomalies.append(stop_anomaly)

        # 4. 時間帯異常チェック
        time_anomaly = self._check_time_anomaly()
        if time_anomaly.is_anomalous:
            anomalies.append(time_anomaly)

        if not anomalies:
            return AnomalyResult(
                is_anomalous=False,
                message="異常なし",
            )

        # 最も重大な異常を返す
        severity_order = {
            AlertSeverity.EMERGENCY: 4,
            AlertSeverity.CRITICAL: 3,
            AlertSeverity.WARNING: 2,
            AlertSeverity.INFO: 1,
        }
        anomalies.sort(
            key=lambda a: severity_order.get(AlertSeverity(a.severity), 0),
            reverse=True,
        )

        return anomalies[0]

    def _check_speed_anomaly(self, speed: float) -> AnomalyResult:
        """速度の異常をチェックする"""
        if speed >= self.VEHICLE_SPEED_THRESHOLD:
            return AnomalyResult(
                is_anomalous=True,
                anomaly_type=AlertType.SPEED_ANOMALY,
                severity=AlertSeverity.CRITICAL,
                confidence=0.9,
                message=f"車両に乗っている可能性があります（速度: {speed:.1f} m/s ≈ {speed * 3.6:.0f} km/h）",
                details={"speed_mps": speed, "speed_kmh": speed * 3.6},
            )
        elif speed > self.RUNNING_SPEED_MAX:
            return AnomalyResult(
                is_anomalous=True,
                anomaly_type=AlertType.SPEED_ANOMALY,
                severity=AlertSeverity.WARNING,
                confidence=0.7,
                message=f"通常より速い移動速度を検知しました（速度: {speed:.1f} m/s ≈ {speed * 3.6:.0f} km/h）",
                details={"speed_mps": speed, "speed_kmh": speed * 3.6},
            )

        return AnomalyResult(is_anomalous=False)

    async def _check_route_deviation(
        self,
        child_id: uuid.UUID,
        latitude: float,
        longitude: float,
    ) -> AnomalyResult:
        """推奨ルートからの逸脱をチェックする"""
        # 推奨ルートを取得
        result = await self.db.execute(
            select(Route).where(
                Route.child_id == child_id,
                Route.is_recommended == True,
                Route.is_active == True,
            ).limit(1)
        )
        route = result.scalar_one_or_none()

        if route is None:
            return AnomalyResult(is_anomalous=False)

        # ルートのウェイポイント（PostGIS LINESTRING）との距離を計算
        # 簡易実装: 出発地・目的地との距離で判定
        # 本来はST_Distance(point, linestring)を使用
        _min_distance = float("inf")  # TODO: use with ST_Distance

        # 直近の位置履歴からルートとの距離を推定
        recent_result = await self.db.execute(
            select(Location)
            .where(Location.child_id == child_id)
            .order_by(desc(Location.timestamp))
            .limit(5)
        )
        recent_locations = recent_result.scalars().all()

        if len(recent_locations) < 2:
            return AnomalyResult(is_anomalous=False)

        # 移動の一貫性をチェック（急な方向転換がないか）
        # 簡易的に前回位置との距離で判定
        prev = recent_locations[1] if len(recent_locations) > 1 else None
        if prev:
            distance_from_prev = self._haversine_distance(
                prev.latitude, prev.longitude, latitude, longitude
            )
            # 前回からの距離が異常に大きい場合
            prev_ts = prev.timestamp.astimezone(timezone.utc) if prev.timestamp.tzinfo else prev.timestamp.replace(tzinfo=timezone.utc)
            time_diff = (
                datetime.now(timezone.utc) - prev_ts
            ).total_seconds()
            if time_diff > 0 and distance_from_prev / time_diff > self.VEHICLE_SPEED_THRESHOLD:
                return AnomalyResult(
                    is_anomalous=True,
                    anomaly_type=AlertType.ROUTE_DEVIATION,
                    severity=AlertSeverity.WARNING,
                    confidence=0.6,
                    message="通常のルートから逸脱している可能性があります",
                    details={
                        "distance_from_previous": distance_from_prev,
                        "time_diff_seconds": time_diff,
                    },
                )

        return AnomalyResult(is_anomalous=False)

    async def _check_unusual_stop(
        self,
        child_id: uuid.UUID,
        latitude: float,
        longitude: float,
        speed: float | None,
    ) -> AnomalyResult:
        """異常な停止をチェックする"""
        if speed is not None and speed > self.STOP_SPEED_THRESHOLD:
            return AnomalyResult(is_anomalous=False)

        # 直近の位置履歴で同じ場所にいる時間を確認
        result = await self.db.execute(
            select(Location)
            .where(Location.child_id == child_id)
            .order_by(desc(Location.timestamp))
            .limit(20)
        )
        recent = result.scalars().all()

        if len(recent) < 2:
            return AnomalyResult(is_anomalous=False)

        # 同じ場所（50m以内）にいる連続ポイントを数える
        stop_start = recent[0].timestamp
        for loc in recent[1:]:
            distance = self._haversine_distance(
                latitude, longitude, loc.latitude, loc.longitude
            )
            if distance > 50:
                break
            stop_start = loc.timestamp

        stop_start_utc = stop_start.astimezone(timezone.utc) if stop_start.tzinfo else stop_start.replace(tzinfo=timezone.utc)
        stop_duration = (
            datetime.now(timezone.utc) - stop_start_utc
        ).total_seconds()

        if stop_duration >= self.STOP_DURATION_CRITICAL:
            return AnomalyResult(
                is_anomalous=True,
                anomaly_type=AlertType.ROUTE_DEVIATION,
                severity=AlertSeverity.CRITICAL,
                confidence=0.8,
                message=f"同じ場所に{int(stop_duration / 60)}分間停止しています",
                details={
                    "stop_duration_seconds": stop_duration,
                    "stop_latitude": latitude,
                    "stop_longitude": longitude,
                },
            )
        elif stop_duration >= self.STOP_DURATION_WARNING:
            return AnomalyResult(
                is_anomalous=True,
                anomaly_type=AlertType.ROUTE_DEVIATION,
                severity=AlertSeverity.WARNING,
                confidence=0.6,
                message=f"同じ場所に{int(stop_duration / 60)}分間停止しています",
                details={
                    "stop_duration_seconds": stop_duration,
                },
            )

        return AnomalyResult(is_anomalous=False)

    def _check_time_anomaly(self) -> AnomalyResult:
        """時間帯の異常をチェックする（日本時間基準）"""
        now_utc = datetime.now(timezone.utc)
        # JST = UTC + 9
        jst_hour = (now_utc.hour + 9) % 24

        # 深夜・早朝（22時〜5時）の移動は異常
        if jst_hour >= 22 or jst_hour < 5:
            return AnomalyResult(
                is_anomalous=True,
                anomaly_type=AlertType.ROUTE_DEVIATION,
                severity=AlertSeverity.CRITICAL,
                confidence=0.95,
                message=f"深夜・早朝の移動を検知しました（現在 {jst_hour}時）",
                details={"jst_hour": jst_hour},
            )
        # 夜間（20時〜22時）の移動は注意
        elif jst_hour >= 20:
            return AnomalyResult(
                is_anomalous=True,
                anomaly_type=AlertType.ROUTE_DEVIATION,
                severity=AlertSeverity.WARNING,
                confidence=0.7,
                message=f"夜間の移動を検知しました（現在 {jst_hour}時）",
                details={"jst_hour": jst_hour},
            )

        return AnomalyResult(is_anomalous=False)

    @staticmethod
    def _haversine_distance(
        lat1: float, lng1: float, lat2: float, lng2: float
    ) -> float:
        """2点間の距離（メートル）"""
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lng2 - lng1)

        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

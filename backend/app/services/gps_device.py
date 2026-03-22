"""GPSデバイスアダプタ — 複数デバイスメーカー対応"""

import hmac
import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.child import Child
from app.models.location import Location, LocationSource
from app.services.anomaly_detector import AnomalyDetector
from app.services.alert_service import AlertService
from app.services.websocket_manager import ws_manager
from app.schemas.location import LocationResponse

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class DeviceLocation:
    """デバイスから受信した位置情報（正規化済み）"""
    device_id: str
    latitude: float
    longitude: float
    altitude: float | None = None
    speed: float | None = None
    accuracy: float | None = None
    heading: float | None = None
    battery_level: float | None = None
    timestamp: datetime | None = None


class GPSDeviceAdapter(ABC):
    """GPSデバイスアダプタの基底クラス"""

    @abstractmethod
    def parse_webhook(self, payload: dict, headers: dict | None = None) -> list[DeviceLocation]:
        """Webhookペイロードをパースして正規化された位置情報リストを返す"""
        ...

    @abstractmethod
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Webhookの署名を検証する"""
        ...


class BoTAdapter(GPSDeviceAdapter):
    """
    BoT (Bsize) GPSトラッカー アダプタ

    BoTは子ども向けGPSトラッカーで、Webhook経由で位置情報を送信する。
    Webhook形式:
    {
        "device_id": "BOT_XXXXXX",
        "events": [
            {
                "type": "location",
                "latitude": 35.6812,
                "longitude": 139.7671,
                "accuracy": 10.0,
                "speed": 1.2,
                "battery": 85,
                "timestamp": "2026-03-10T10:00:00Z"
            }
        ]
    }
    """

    def __init__(self, webhook_secret: str = ""):
        self.webhook_secret = webhook_secret or settings.BOT_WEBHOOK_SECRET

    def parse_webhook(self, payload: dict, headers: dict | None = None) -> list[DeviceLocation]:
        device_id = payload.get("device_id", "")
        events = payload.get("events", [])
        locations = []

        for event in events:
            if event.get("type") != "location":
                continue

            ts = event.get("timestamp")
            timestamp = None
            if ts:
                try:
                    timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    timestamp = datetime.now(timezone.utc)

            locations.append(DeviceLocation(
                device_id=device_id,
                latitude=float(event["latitude"]),
                longitude=float(event["longitude"]),
                accuracy=event.get("accuracy"),
                speed=event.get("speed"),
                battery_level=event.get("battery"),
                timestamp=timestamp or datetime.now(timezone.utc),
            ))

        return locations

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        if not self.webhook_secret:
            return True  # シークレット未設定時はスキップ（開発用）
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


class MitsuneAdapter(GPSDeviceAdapter):
    """
    みつね GPSトラッカー アダプタ

    Webhook形式:
    {
        "imei": "XXXXXXXXX",
        "data": [
            {
                "lat": 35.6812,
                "lng": 139.7671,
                "alt": 40.0,
                "spd": 0.5,
                "bat": 72,
                "acc": 15.0,
                "ts": 1710000000
            }
        ]
    }
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.MITSUNE_API_KEY

    def parse_webhook(self, payload: dict, headers: dict | None = None) -> list[DeviceLocation]:
        device_id = payload.get("imei", "")
        data_list = payload.get("data", [])
        locations = []

        for data in data_list:
            ts = data.get("ts")
            timestamp = (
                datetime.fromtimestamp(ts, tz=timezone.utc) if ts
                else datetime.now(timezone.utc)
            )

            locations.append(DeviceLocation(
                device_id=device_id,
                latitude=float(data["lat"]),
                longitude=float(data["lng"]),
                altitude=data.get("alt"),
                speed=data.get("spd"),
                accuracy=data.get("acc"),
                battery_level=data.get("bat"),
                timestamp=timestamp,
            ))

        return locations

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        if not self.api_key:
            return True
        expected = hmac.new(
            self.api_key.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


class GenericAdapter(GPSDeviceAdapter):
    """
    汎用GPSデバイスアダプタ（カスタムデバイス用）

    Webhook形式:
    {
        "device_id": "XXXXX",
        "latitude": 35.6812,
        "longitude": 139.7671,
        "speed": 1.0,
        "battery": 80,
        "timestamp": "2026-03-10T10:00:00Z"
    }
    """

    def parse_webhook(self, payload: dict, headers: dict | None = None) -> list[DeviceLocation]:
        ts = payload.get("timestamp")
        timestamp = None
        if ts:
            try:
                timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        return [DeviceLocation(
            device_id=payload.get("device_id", "unknown"),
            latitude=float(payload["latitude"]),
            longitude=float(payload["longitude"]),
            altitude=payload.get("altitude"),
            speed=payload.get("speed"),
            accuracy=payload.get("accuracy"),
            heading=payload.get("heading"),
            battery_level=payload.get("battery"),
            timestamp=timestamp or datetime.now(timezone.utc),
        )]

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        return True


# デバイス種別 → アダプタ マッピング
DEVICE_ADAPTERS: dict[str, type[GPSDeviceAdapter]] = {
    "bot": BoTAdapter,
    "mitsune": MitsuneAdapter,
    "generic": GenericAdapter,
}


def get_adapter(device_type: str) -> GPSDeviceAdapter:
    """デバイス種別に応じたアダプタを取得する"""
    adapter_cls = DEVICE_ADAPTERS.get(device_type, GenericAdapter)
    return adapter_cls()


async def process_device_locations(
    db: AsyncSession,
    device_locations: list[DeviceLocation],
) -> list[Location]:
    """
    デバイスから受信した位置情報を処理する。
    1. device_id から子どもを特定
    2. 位置情報をDBに保存
    3. 異常検知を実行
    4. WebSocketでリアルタイム配信
    """
    saved_locations = []

    for dev_loc in device_locations:
        # device_id から子どもを特定
        result = await db.execute(
            select(Child).where(
                Child.device_id == dev_loc.device_id,
                Child.is_active == True,
            )
        )
        child = result.scalar_one_or_none()

        if child is None:
            logger.warning(f"不明なデバイスID: {dev_loc.device_id}")
            continue

        # 位置情報を保存
        location = Location(
            child_id=child.id,
            latitude=dev_loc.latitude,
            longitude=dev_loc.longitude,
            altitude=dev_loc.altitude,
            speed=dev_loc.speed,
            accuracy=dev_loc.accuracy,
            heading=dev_loc.heading,
            source=LocationSource.GPS_DEVICE,
            battery_level=dev_loc.battery_level,
            timestamp=dev_loc.timestamp or datetime.now(timezone.utc),
        )
        db.add(location)
        await db.flush()
        await db.refresh(location)
        saved_locations.append(location)

        # 異常検知
        try:
            detector = AnomalyDetector(db)
            anomaly = await detector.detect_anomaly(
                child_id=child.id,
                latitude=dev_loc.latitude,
                longitude=dev_loc.longitude,
                speed=dev_loc.speed,
            )
            if anomaly and anomaly.is_anomalous:
                alert_service = AlertService(db)
                await alert_service.create_alert_from_anomaly(
                    child_id=child.id,
                    user_id=child.user_id,
                    anomaly=anomaly,
                    latitude=dev_loc.latitude,
                    longitude=dev_loc.longitude,
                )
        except Exception as e:
            logger.error(f"異常検知失敗: {e}")

        # WebSocketでリアルタイム配信
        try:
            loc_response = LocationResponse.model_validate(location)
            await ws_manager.broadcast_location(
                child_id=child.id,
                location_data=loc_response.model_dump(mode="json"),
            )
        except Exception:
            pass

    return saved_locations

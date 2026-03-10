"""GPSデバイスアダプタのユニットテスト"""

import pytest

from app.services.gps_device import BoTAdapter, MitsuneAdapter, GenericAdapter, get_adapter


class TestBoTAdapter:
    """BoTアダプタのテスト"""

    def setup_method(self):
        self.adapter = BoTAdapter(webhook_secret="")

    def test_parse_location_event(self):
        """位置情報イベントのパース"""
        payload = {
            "device_id": "BOT_001",
            "events": [
                {
                    "type": "location",
                    "latitude": 35.6812,
                    "longitude": 139.7671,
                    "accuracy": 10.0,
                    "speed": 1.2,
                    "battery": 85,
                    "timestamp": "2026-03-10T10:00:00Z",
                }
            ],
        }
        locations = self.adapter.parse_webhook(payload)
        assert len(locations) == 1
        loc = locations[0]
        assert loc.device_id == "BOT_001"
        assert loc.latitude == 35.6812
        assert loc.longitude == 139.7671
        assert loc.speed == 1.2
        assert loc.battery_level == 85

    def test_skip_non_location_events(self):
        """位置情報以外のイベントはスキップ"""
        payload = {
            "device_id": "BOT_001",
            "events": [
                {"type": "battery", "level": 50},
                {"type": "location", "latitude": 35.68, "longitude": 139.77},
            ],
        }
        locations = self.adapter.parse_webhook(payload)
        assert len(locations) == 1

    def test_empty_events(self):
        """イベントなしは空リスト"""
        payload = {"device_id": "BOT_001", "events": []}
        locations = self.adapter.parse_webhook(payload)
        assert len(locations) == 0

    def test_multiple_events(self):
        """複数イベントのパース"""
        payload = {
            "device_id": "BOT_001",
            "events": [
                {"type": "location", "latitude": 35.68, "longitude": 139.77, "timestamp": "2026-03-10T10:00:00Z"},
                {"type": "location", "latitude": 35.69, "longitude": 139.78, "timestamp": "2026-03-10T10:05:00Z"},
            ],
        }
        locations = self.adapter.parse_webhook(payload)
        assert len(locations) == 2

    def test_verify_signature_no_secret(self):
        """シークレット未設定時は常にTrue"""
        assert self.adapter.verify_signature(b"test", "any")


class TestMitsuneAdapter:
    """みつねアダプタのテスト"""

    def setup_method(self):
        self.adapter = MitsuneAdapter(api_key="")

    def test_parse_data(self):
        payload = {
            "imei": "MITSUNE_001",
            "data": [
                {
                    "lat": 35.6812,
                    "lng": 139.7671,
                    "alt": 40.0,
                    "spd": 0.5,
                    "bat": 72,
                    "acc": 15.0,
                    "ts": 1741600000,
                }
            ],
        }
        locations = self.adapter.parse_webhook(payload)
        assert len(locations) == 1
        loc = locations[0]
        assert loc.device_id == "MITSUNE_001"
        assert loc.altitude == 40.0
        assert loc.battery_level == 72


class TestGenericAdapter:
    """汎用アダプタのテスト"""

    def setup_method(self):
        self.adapter = GenericAdapter()

    def test_parse_single_location(self):
        payload = {
            "device_id": "GENERIC_001",
            "latitude": 35.6812,
            "longitude": 139.7671,
            "speed": 1.0,
            "battery": 80,
            "timestamp": "2026-03-10T10:00:00Z",
        }
        locations = self.adapter.parse_webhook(payload)
        assert len(locations) == 1
        assert locations[0].device_id == "GENERIC_001"


class TestGetAdapter:
    """アダプタ取得のテスト"""

    def test_get_bot_adapter(self):
        adapter = get_adapter("bot")
        assert isinstance(adapter, BoTAdapter)

    def test_get_mitsune_adapter(self):
        adapter = get_adapter("mitsune")
        assert isinstance(adapter, MitsuneAdapter)

    def test_get_generic_adapter(self):
        adapter = get_adapter("generic")
        assert isinstance(adapter, GenericAdapter)

    def test_unknown_type_falls_back_to_generic(self):
        adapter = get_adapter("unknown_device")
        assert isinstance(adapter, GenericAdapter)

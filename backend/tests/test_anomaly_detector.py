"""異常検知サービスのユニットテスト"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.anomaly_detector import AnomalyDetector
from app.models.alert import AlertType, AlertSeverity


class TestSpeedAnomaly:
    """速度異常検知のテスト"""

    def setup_method(self):
        self.db = AsyncMock()
        self.detector = AnomalyDetector(self.db)

    def test_normal_walking_speed(self):
        """正常な歩行速度ではアラートなし"""
        result = self.detector._check_speed_anomaly(1.5)  # 1.5 m/s ≈ 5.4 km/h
        assert not result.is_anomalous

    def test_running_speed(self):
        """走行速度はアラートなし"""
        result = self.detector._check_speed_anomaly(3.5)  # 3.5 m/s ≈ 12.6 km/h
        assert not result.is_anomalous

    def test_above_running_speed_warning(self):
        """走行速度超過で警告"""
        result = self.detector._check_speed_anomaly(5.0)  # 5.0 m/s ≈ 18 km/h
        assert result.is_anomalous
        assert result.severity == AlertSeverity.WARNING
        assert result.anomaly_type == AlertType.SPEED_ANOMALY

    def test_vehicle_speed_critical(self):
        """車両速度でクリティカル"""
        result = self.detector._check_speed_anomaly(10.0)  # 10 m/s ≈ 36 km/h
        assert result.is_anomalous
        assert result.severity == AlertSeverity.CRITICAL
        assert result.confidence == 0.9

    def test_zero_speed(self):
        """速度0はアラートなし"""
        result = self.detector._check_speed_anomaly(0.0)
        assert not result.is_anomalous


class TestTimeAnomaly:
    """時間帯異常検知のテスト"""

    def setup_method(self):
        self.db = AsyncMock()
        self.detector = AnomalyDetector(self.db)

    @patch("app.services.anomaly_detector.datetime")
    def test_late_night_critical(self, mock_datetime):
        """深夜（JST 23時 = UTC 14時）はクリティカル"""
        mock_now = datetime(2026, 3, 10, 14, 0, 0, tzinfo=timezone.utc)  # JST 23時
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = self.detector._check_time_anomaly()
        assert result.is_anomalous
        assert result.severity == AlertSeverity.CRITICAL

    @patch("app.services.anomaly_detector.datetime")
    def test_daytime_no_anomaly(self, mock_datetime):
        """昼間（JST 10時 = UTC 1時）は正常"""
        mock_now = datetime(2026, 3, 10, 1, 0, 0, tzinfo=timezone.utc)  # JST 10時
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = self.detector._check_time_anomaly()
        assert not result.is_anomalous

    @patch("app.services.anomaly_detector.datetime")
    def test_evening_warning(self, mock_datetime):
        """夜間（JST 21時 = UTC 12時）は警告"""
        mock_now = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)  # JST 21時
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = self.detector._check_time_anomaly()
        assert result.is_anomalous
        assert result.severity == AlertSeverity.WARNING


class TestHaversineDistance:
    """ハーバーサイン距離計算のテスト"""

    def test_same_point(self):
        """同一地点の距離は0"""
        dist = AnomalyDetector._haversine_distance(35.68, 139.76, 35.68, 139.76)
        assert dist == 0.0

    def test_known_distance(self):
        """東京駅→新宿駅（約6.5km）"""
        dist = AnomalyDetector._haversine_distance(
            35.6812, 139.7671,  # 東京駅付近
            35.6896, 139.7006,  # 新宿駅付近
        )
        assert 5500 < dist < 7500  # 6km前後

    def test_short_distance(self):
        """近距離（数百メートル）"""
        dist = AnomalyDetector._haversine_distance(
            35.6812, 139.7671,
            35.6822, 139.7681,
        )
        assert 100 < dist < 200  # 約140m

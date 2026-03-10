"""危険エリア分析サービスのユニットテスト"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.danger_analyzer import DangerAnalyzer, TimeOfDay
from app.models.danger_zone import DangerZone, RiskType, DangerZoneSource


class TestTimeOfDay:
    """時間帯判定のテスト"""

    def test_morning(self):
        dt = datetime(2026, 3, 10, 7, 30, tzinfo=timezone.utc)
        assert DangerAnalyzer._get_time_of_day(dt) == TimeOfDay.MORNING

    def test_daytime(self):
        dt = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
        assert DangerAnalyzer._get_time_of_day(dt) == TimeOfDay.DAYTIME

    def test_afternoon(self):
        dt = datetime(2026, 3, 10, 16, 0, tzinfo=timezone.utc)
        assert DangerAnalyzer._get_time_of_day(dt) == TimeOfDay.AFTERNOON

    def test_evening(self):
        dt = datetime(2026, 3, 10, 19, 0, tzinfo=timezone.utc)
        assert DangerAnalyzer._get_time_of_day(dt) == TimeOfDay.EVENING

    def test_night(self):
        dt = datetime(2026, 3, 10, 23, 0, tzinfo=timezone.utc)
        assert DangerAnalyzer._get_time_of_day(dt) == TimeOfDay.NIGHT

    def test_early_morning_is_night(self):
        dt = datetime(2026, 3, 10, 3, 0, tzinfo=timezone.utc)
        assert DangerAnalyzer._get_time_of_day(dt) == TimeOfDay.NIGHT


class TestRecommendation:
    """推奨メッセージ生成のテスト"""

    def test_high_risk_message(self):
        msg = DangerAnalyzer._generate_recommendation(8.0, "crime", TimeOfDay.EVENING)
        assert "リスクが高い" in msg
        assert "犯罪" in msg
        assert "夜間" in msg

    def test_medium_risk_message(self):
        msg = DangerAnalyzer._generate_recommendation(5.5, "traffic", TimeOfDay.DAYTIME)
        assert "注意が必要" in msg
        assert "交通" in msg

    def test_low_risk_message(self):
        msg = DangerAnalyzer._generate_recommendation(3.0, None, TimeOfDay.MORNING)
        assert "比較的安全" in msg

    def test_night_time_warning(self):
        msg = DangerAnalyzer._generate_recommendation(3.0, None, TimeOfDay.NIGHT)
        assert "夜間" in msg


class TestAnalyzeAreaRisk:
    """エリアリスク分析のテスト"""

    @pytest.fixture(autouse=True)
    def setup(self, mock_db):
        self.db = mock_db
        self.analyzer = DangerAnalyzer(self.db)

    @pytest.mark.asyncio
    async def test_no_danger_zones(self):
        """危険ゾーンがない場合のスコア"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(self.analyzer, "_get_danger_zones_in_area", AsyncMock(return_value=[]))

            result = await self.analyzer.analyze_area_risk(
                latitude=35.68, longitude=139.77
            )

            assert result.risk_score.overall >= 1.0
            assert result.danger_zones_count == 0
            assert "安全" in result.recommendation

    @pytest.mark.asyncio
    async def test_with_crime_zone(self, sample_danger_zones):
        """犯罪ゾーンがある場合のスコア上昇"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                self.analyzer, "_get_danger_zones_in_area",
                AsyncMock(return_value=sample_danger_zones),
            )

            result = await self.analyzer.analyze_area_risk(
                latitude=35.685, longitude=139.770
            )

            assert result.danger_zones_count == 2
            assert result.risk_score.overall > 1.0

    @pytest.mark.asyncio
    async def test_night_multiplier(self, sample_danger_zones):
        """夜間は時間帯補正でリスクスコアが上がる"""
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                self.analyzer, "_get_danger_zones_in_area",
                AsyncMock(return_value=sample_danger_zones),
            )

            # 昼間
            day_result = await self.analyzer.analyze_area_risk(
                latitude=35.685, longitude=139.770,
                time=datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc),
            )

            # 夜間
            night_result = await self.analyzer.analyze_area_risk(
                latitude=35.685, longitude=139.770,
                time=datetime(2026, 3, 10, 23, 0, tzinfo=timezone.utc),
            )

            assert night_result.risk_score.overall >= day_result.risk_score.overall

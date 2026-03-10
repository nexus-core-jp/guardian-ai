"""ルートエンジンのユニットテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.route_engine import RouteEngine, RiskFactor


class TestFallbackGeometry:
    """フォールバックジオメトリのテスト"""

    def setup_method(self):
        self.db = AsyncMock()
        self.engine = RouteEngine(self.db)

    def test_fallback_creates_points(self):
        """フォールバックで正しい数のポイントが生成される"""
        geom = self.engine._fallback_geometry(35.68, 139.77, 35.66, 139.70, num_points=5)
        assert len(geom) == 6  # num_points + 1

    def test_fallback_starts_at_origin(self):
        geom = self.engine._fallback_geometry(35.68, 139.77, 35.66, 139.70)
        assert geom[0] == (35.68, 139.77)

    def test_fallback_ends_at_destination(self):
        geom = self.engine._fallback_geometry(35.68, 139.77, 35.66, 139.70)
        assert abs(geom[-1][0] - 35.66) < 1e-10
        assert abs(geom[-1][1] - 139.70) < 1e-10


class TestGeometryToWaypoints:
    """ジオメトリ→ウェイポイント変換のテスト"""

    def setup_method(self):
        self.db = AsyncMock()
        self.engine = RouteEngine(self.db)

    def test_short_geometry_no_sampling(self):
        """短いジオメトリはそのまま変換"""
        geom = [(35.68 + i * 0.001, 139.77 + i * 0.001) for i in range(10)]
        waypoints = self.engine._geometry_to_waypoints(geom, max_points=50)
        assert len(waypoints) == 10
        assert waypoints[0].order == 0
        assert waypoints[9].order == 9

    def test_long_geometry_sampled(self):
        """長いジオメトリは間引かれる"""
        geom = [(35.68 + i * 0.0001, 139.77 + i * 0.0001) for i in range(200)]
        waypoints = self.engine._geometry_to_waypoints(geom, max_points=30)
        assert len(waypoints) == 30
        # 最後の点は目的地
        assert abs(waypoints[-1].latitude - geom[-1][0]) < 1e-10

    def test_preserves_endpoints(self):
        """始点と終点が保持される"""
        geom = [(35.68 + i * 0.0001, 139.77 + i * 0.0001) for i in range(100)]
        waypoints = self.engine._geometry_to_waypoints(geom, max_points=20)
        assert waypoints[0].latitude == geom[0][0]
        assert waypoints[-1].latitude == geom[-1][0]


class TestPolylineDistance:
    """ポリライン距離計算のテスト"""

    def setup_method(self):
        self.db = AsyncMock()
        self.engine = RouteEngine(self.db)

    def test_single_segment(self):
        """1セグメントの距離"""
        geom = [(35.68, 139.77), (35.69, 139.78)]
        dist = self.engine._polyline_distance(geom)
        assert dist > 0
        assert 1000 < dist < 2000

    def test_multiple_segments(self):
        """複数セグメントの距離は合計"""
        geom = [
            (35.68, 139.77),
            (35.69, 139.78),
            (35.70, 139.79),
        ]
        total = self.engine._polyline_distance(geom)
        seg1 = self.engine._polyline_distance(geom[:2])
        seg2 = self.engine._polyline_distance(geom[1:])
        assert abs(total - (seg1 + seg2)) < 0.01

    def test_single_point(self):
        """1点のみは距離0"""
        geom = [(35.68, 139.77)]
        dist = self.engine._polyline_distance(geom)
        assert dist == 0.0


class TestDetourWaypoint:
    """迂回ウェイポイント計算のテスト"""

    def setup_method(self):
        self.db = AsyncMock()
        self.engine = RouteEngine(self.db)

    def test_no_risk_zones(self):
        """リスクゾーンなしは迂回なし"""
        result = self.engine._compute_detour_waypoint(
            35.68, 139.77, 35.66, 139.70, []
        )
        assert result is None

    def test_detour_away_from_danger(self):
        """迂回ポイントは危険ゾーンから離れる方向"""
        danger = [RiskFactor(
            latitude=35.67, longitude=139.735,
            risk_level=8, risk_type="crime", radius_meters=100,
        )]
        result = self.engine._compute_detour_waypoint(
            35.68, 139.77, 35.66, 139.70, danger
        )
        assert result is not None
        wp_lat, wp_lng = result
        # 中点付近にある
        assert 35.65 < wp_lat < 35.70
        assert 139.69 < wp_lng < 139.78

    def test_multiple_dangers_weighted(self):
        """複数の危険ゾーンはリスク加重で重心計算"""
        dangers = [
            RiskFactor(latitude=35.67, longitude=139.735,
                       risk_level=9, risk_type="crime", radius_meters=100),
            RiskFactor(latitude=35.675, longitude=139.740,
                       risk_level=3, risk_type="traffic", radius_meters=150),
        ]
        result = self.engine._compute_detour_waypoint(
            35.68, 139.77, 35.66, 139.70, dangers
        )
        assert result is not None


class TestSafetyScore:
    """安全スコア計算のテスト"""

    def setup_method(self):
        self.db = AsyncMock()
        self.engine = RouteEngine(self.db)

    @pytest.mark.asyncio
    async def test_no_danger_high_score(self):
        """危険ゾーンなしは高スコア"""
        geom = [(35.68 + i * 0.001, 139.77 + i * 0.001) for i in range(5)]
        score = await self.engine._calculate_safety_score(geom, [], None)
        assert score.overall >= 8.0

    @pytest.mark.asyncio
    async def test_nearby_danger_lowers_score(self):
        """近くに危険ゾーンがあるとスコア低下"""
        geom = [(35.68 + i * 0.001, 139.77 + i * 0.001) for i in range(5)]
        dangers = [RiskFactor(
            latitude=35.681, longitude=139.771,
            risk_level=8, risk_type="crime", radius_meters=200,
        )]

        score_safe = await self.engine._calculate_safety_score(geom, [], None)
        score_danger = await self.engine._calculate_safety_score(geom, dangers, None)

        assert score_danger.overall < score_safe.overall

    @pytest.mark.asyncio
    async def test_night_lowers_score(self):
        """夜間はスコア低下"""
        geom = [(35.68 + i * 0.001, 139.77 + i * 0.001) for i in range(5)]

        score_day = await self.engine._calculate_safety_score(geom, [], "morning")
        score_night = await self.engine._calculate_safety_score(geom, [], "night")

        assert score_night.overall < score_day.overall

    @pytest.mark.asyncio
    async def test_score_range(self):
        """スコアは1.0〜10.0の範囲"""
        geom = [(35.68, 139.77)]
        many_dangers = [
            RiskFactor(latitude=35.68, longitude=139.77,
                       risk_level=10, risk_type="crime", radius_meters=500)
            for _ in range(20)
        ]
        score = await self.engine._calculate_safety_score(geom, many_dangers, "night")
        assert 1.0 <= score.overall <= 10.0
        assert 1.0 <= score.traffic_safety <= 10.0
        assert 1.0 <= score.crime_safety <= 10.0

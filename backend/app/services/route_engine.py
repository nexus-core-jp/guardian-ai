"""AI安全ルート計算エンジン — OSRM/Mapbox統合版"""

import uuid
import math
import logging
from datetime import datetime, timezone
from dataclasses import dataclass

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.child import School
from app.models.route import Route
from app.models.danger_zone import DangerZone
from app.schemas.route import (
    RouteCalculateResponse,
    RouteResponse,
    RoutePoint,
    RouteWaypoint,
    SafetyScoreBreakdown,
)

settings = get_settings()
logger = logging.getLogger(__name__)

# OSRM公開サーバー（本番ではセルフホストを推奨）
OSRM_BASE_URL = "https://router.project-osrm.org"


@dataclass
class RiskFactor:
    """リスク要因"""
    latitude: float
    longitude: float
    risk_level: int
    risk_type: str
    radius_meters: float


class RouteEngine:
    """
    安全ルート計算エンジン
    OSRM（またはMapbox Directions API）で実際の道路ネットワーク上のルートを取得し、
    危険エリアとの近接度でリスクスコアを計算する。
    危険エリアが多い場合は迂回ウェイポイントを生成して代替ルートも提案する。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_safe_route(
        self,
        origin_lat: float,
        origin_lng: float,
        destination_lat: float | None = None,
        destination_lng: float | None = None,
        child_id: uuid.UUID | None = None,
        school_id: uuid.UUID | None = None,
        time_of_day: str | None = None,
        avoid_danger_zones: bool = True,
    ) -> RouteCalculateResponse | None:
        """安全ルートを計算する"""
        # 学校IDから目的地座標を取得
        if school_id and (destination_lat is None or destination_lng is None):
            school = await self._get_school(school_id)
            if school is None or school.latitude is None or school.longitude is None:
                return None
            destination_lat = school.latitude
            destination_lng = school.longitude

        if destination_lat is None or destination_lng is None:
            return None

        # 危険エリアを取得
        danger_zones: list[RiskFactor] = []
        if avoid_danger_zones:
            danger_zones = await self._get_nearby_danger_zones(
                origin_lat, origin_lng, destination_lat, destination_lng
            )

        # --- メインルート: OSRMで道路ネットワーク上のルートを取得 ---
        main_geometry = await self._fetch_osrm_route(
            origin_lat, origin_lng, destination_lat, destination_lng
        )

        if main_geometry is None:
            # OSRM到達不能時はフォールバック（直線補間）
            logger.warning("OSRM到達不能 — フォールバックルートを生成")
            main_geometry = self._fallback_geometry(
                origin_lat, origin_lng, destination_lat, destination_lng
            )

        # --- 危険エリアが多い場合は迂回ルートも取得 ---
        high_risk_zones = [z for z in danger_zones if z.risk_level >= 6]
        alternative_routes: list[RouteResponse] = []

        if high_risk_zones and avoid_danger_zones:
            detour_wp = self._compute_detour_waypoint(
                origin_lat, origin_lng,
                destination_lat, destination_lng,
                high_risk_zones,
            )
            if detour_wp:
                alt_geometry = await self._fetch_osrm_route(
                    origin_lat, origin_lng,
                    destination_lat, destination_lng,
                    via_lat=detour_wp[0], via_lng=detour_wp[1],
                )
                if alt_geometry:
                    alt_waypoints = self._geometry_to_waypoints(alt_geometry)
                    alt_distance = self._polyline_distance(alt_geometry)
                    alt_duration = alt_distance / 58.0  # 小学生歩行速度 58 m/min
                    alt_safety = await self._calculate_safety_score(
                        alt_geometry, danger_zones, time_of_day
                    )
                    alt_route = RouteResponse(
                        id=uuid.uuid4(),
                        child_id=child_id or uuid.uuid4(),
                        name="迂回ルート",
                        origin=RoutePoint(latitude=origin_lat, longitude=origin_lng),
                        destination=RoutePoint(latitude=destination_lat, longitude=destination_lng),
                        waypoints=alt_waypoints,
                        distance_meters=alt_distance,
                        estimated_duration_minutes=alt_duration,
                        safety_score=alt_safety.overall,
                        is_recommended=False,
                        is_active=True,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    alternative_routes.append(alt_route)

        # --- メインルートのスコアリング ---
        waypoints = self._geometry_to_waypoints(main_geometry)
        distance = self._polyline_distance(main_geometry)
        walking_speed_mpm = 58.0  # 小学生平均歩行速度 m/min
        estimated_minutes = distance / walking_speed_mpm

        safety_breakdown = await self._calculate_safety_score(
            main_geometry, danger_zones, time_of_day
        )

        # 迂回ルートの方が安全スコアが高い場合はそちらを推奨
        main_is_recommended = True
        if alternative_routes and alternative_routes[0].safety_score > safety_breakdown.overall:
            main_is_recommended = False
            alternative_routes[0].is_recommended = True

        # DBに保存
        if child_id:
            route = Route(
                child_id=child_id,
                name="通学路",
                origin_lat=origin_lat,
                origin_lng=origin_lng,
                destination_lat=destination_lat,
                destination_lng=destination_lng,
                waypoints_json=[wp.model_dump() for wp in waypoints],
                distance_meters=distance,
                estimated_duration_minutes=estimated_minutes,
                safety_score=safety_breakdown.overall,
                is_recommended=main_is_recommended,
                is_active=True,
            )
            self.db.add(route)
            await self.db.flush()
            await self.db.refresh(route)

            route_response = RouteResponse(
                id=route.id,
                child_id=child_id,
                name=route.name,
                origin=RoutePoint(latitude=origin_lat, longitude=origin_lng),
                destination=RoutePoint(latitude=destination_lat, longitude=destination_lng),
                waypoints=waypoints,
                distance_meters=distance,
                estimated_duration_minutes=estimated_minutes,
                safety_score=safety_breakdown.overall,
                is_recommended=main_is_recommended,
                is_active=True,
                created_at=route.created_at,
                updated_at=route.updated_at,
            )
        else:
            route_response = RouteResponse(
                id=uuid.uuid4(),
                child_id=child_id or uuid.uuid4(),
                name="計算ルート",
                origin=RoutePoint(latitude=origin_lat, longitude=origin_lng),
                destination=RoutePoint(latitude=destination_lat, longitude=destination_lng),
                waypoints=waypoints,
                distance_meters=distance,
                estimated_duration_minutes=estimated_minutes,
                safety_score=safety_breakdown.overall,
                is_recommended=main_is_recommended,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

        return RouteCalculateResponse(
            route=route_response,
            safety_breakdown=safety_breakdown,
            alternative_routes=alternative_routes,
            danger_zones_nearby=len(danger_zones),
        )

    # ------------------------------------------------------------------ #
    #  OSRM / Mapbox ルーティング
    # ------------------------------------------------------------------ #

    async def _fetch_osrm_route(
        self,
        origin_lat: float, origin_lng: float,
        dest_lat: float, dest_lng: float,
        via_lat: float | None = None, via_lng: float | None = None,
    ) -> list[tuple[float, float]] | None:
        """
        OSRM（またはMapbox）から道路ネットワーク上のルートを取得する。
        Mapboxトークンが設定されていればMapbox Directions APIを使用。
        なければOSRM公開デモサーバーを使用。

        Returns:
            [(lat, lng), ...] のジオメトリリスト。取得失敗時はNone。
        """
        # 経由地を含めた座標文字列
        coords = f"{origin_lng},{origin_lat}"
        if via_lat is not None and via_lng is not None:
            coords += f";{via_lng},{via_lat}"
        coords += f";{dest_lng},{dest_lat}"

        if settings.MAPBOX_TOKEN:
            url = (
                f"https://api.mapbox.com/directions/v5/mapbox/walking/{coords}"
                f"?geometries=geojson&overview=full&access_token={settings.MAPBOX_TOKEN}"
            )
        else:
            url = (
                f"{OSRM_BASE_URL}/route/v1/foot/{coords}"
                f"?geometries=geojson&overview=full"
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            if data.get("code") != "Ok" or not data.get("routes"):
                logger.warning(f"ルーティングAPI応答異常: {data.get('code')}")
                return None

            route_data = data["routes"][0]
            geojson_coords = route_data["geometry"]["coordinates"]  # [[lng, lat], ...]

            # GeoJSON座標 (lng, lat) → (lat, lng)
            geometry = [(c[1], c[0]) for c in geojson_coords]

            logger.info(
                f"ルート取得成功: {len(geometry)}点, "
                f"距離={route_data.get('distance', 0):.0f}m, "
                f"所要時間={route_data.get('duration', 0):.0f}s"
            )
            return geometry

        except httpx.HTTPStatusError as e:
            logger.error(f"ルーティングAPI HTTPエラー: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"ルーティングAPI呼び出し失敗: {e}")
            return None

    def _fallback_geometry(
        self,
        origin_lat: float, origin_lng: float,
        dest_lat: float, dest_lng: float,
        num_points: int = 10,
    ) -> list[tuple[float, float]]:
        """OSRM到達不能時のフォールバック: 直線補間ジオメトリ"""
        geometry = []
        for i in range(num_points + 1):
            t = i / num_points
            lat = origin_lat + t * (dest_lat - origin_lat)
            lng = origin_lng + t * (dest_lng - origin_lng)
            geometry.append((lat, lng))
        return geometry

    # ------------------------------------------------------------------ #
    #  迂回ウェイポイント計算
    # ------------------------------------------------------------------ #

    def _compute_detour_waypoint(
        self,
        origin_lat: float, origin_lng: float,
        dest_lat: float, dest_lng: float,
        high_risk_zones: list[RiskFactor],
    ) -> tuple[float, float] | None:
        """
        高リスクゾーンから離れる方向に迂回ポイントを計算する。
        ルートの中点から、危険ゾーンの重心と反対方向に300mオフセット。
        """
        if not high_risk_zones:
            return None

        mid_lat = (origin_lat + dest_lat) / 2
        mid_lng = (origin_lng + dest_lng) / 2

        # 危険ゾーンのリスク加重重心
        total_weight = sum(z.risk_level for z in high_risk_zones)
        if total_weight == 0:
            return None

        danger_center_lat = sum(z.latitude * z.risk_level for z in high_risk_zones) / total_weight
        danger_center_lng = sum(z.longitude * z.risk_level for z in high_risk_zones) / total_weight

        # 中点→危険重心のベクトルを求め、反対方向にオフセット
        dlat = mid_lat - danger_center_lat
        dlng = mid_lng - danger_center_lng
        norm = math.sqrt(dlat ** 2 + dlng ** 2)

        if norm < 1e-8:
            # ルートの法線方向にオフセット
            route_dlat = dest_lat - origin_lat
            route_dlng = dest_lng - origin_lng
            dlat = -route_dlng
            dlng = route_dlat
            norm = math.sqrt(dlat ** 2 + dlng ** 2)
            if norm < 1e-8:
                return None

        # 約300mのオフセット（緯度1度≈111km）
        offset_deg = 0.003  # ≈300m
        wp_lat = mid_lat + (dlat / norm) * offset_deg
        wp_lng = mid_lng + (dlng / norm) * offset_deg

        return (wp_lat, wp_lng)

    # ------------------------------------------------------------------ #
    #  ジオメトリ → ウェイポイント変換
    # ------------------------------------------------------------------ #

    def _geometry_to_waypoints(
        self, geometry: list[tuple[float, float]], max_points: int = 50
    ) -> list[RouteWaypoint]:
        """
        OSRMのジオメトリを間引いてRouteWaypointリストに変換する。
        地図表示用に最大max_points点まで簡略化。
        """
        if len(geometry) <= max_points:
            return [
                RouteWaypoint(latitude=lat, longitude=lng, order=i)
                for i, (lat, lng) in enumerate(geometry)
            ]

        # Douglas-Peuckerの代わりに等間隔サンプリング
        step = len(geometry) / (max_points - 1)
        waypoints = []
        for i in range(max_points - 1):
            idx = int(i * step)
            lat, lng = geometry[idx]
            waypoints.append(RouteWaypoint(latitude=lat, longitude=lng, order=i))

        # 最後の点は必ず含める
        lat, lng = geometry[-1]
        waypoints.append(RouteWaypoint(latitude=lat, longitude=lng, order=max_points - 1))
        return waypoints

    # ------------------------------------------------------------------ #
    #  安全スコア計算（ルートジオメトリ × 危険ゾーン）
    # ------------------------------------------------------------------ #

    async def _calculate_safety_score(
        self,
        geometry: list[tuple[float, float]],
        danger_zones: list[RiskFactor],
        time_of_day: str | None = None,
    ) -> SafetyScoreBreakdown:
        """
        ルートのジオメトリに沿って安全スコアを計算する。
        各ジオメトリ点から危険ゾーンへの距離を評価し、
        近い危険ゾーンほど大きなペナルティを与える。
        """
        base_score = 9.0

        # --- 危険ゾーンペナルティ: 距離ベースの減衰 ---
        danger_penalty = 0.0
        crime_penalty = 0.0
        traffic_penalty = 0.0

        if danger_zones and geometry:
            # ジオメトリを間引いてサンプリング（計算量削減）
            sample_step = max(1, len(geometry) // 20)
            sample_points = geometry[::sample_step]

            for zone in danger_zones:
                # サンプル点からの最短距離
                min_dist = min(
                    self._haversine_distance(pt[0], pt[1], zone.latitude, zone.longitude)
                    for pt in sample_points
                )
                zone_radius = zone.radius_meters or 100.0

                if min_dist < zone_radius:
                    # ゾーン内: フルペナルティ
                    proximity_factor = 1.0
                elif min_dist < zone_radius * 3:
                    # ゾーン周辺: 距離に応じて減衰
                    proximity_factor = 1.0 - (min_dist - zone_radius) / (zone_radius * 2)
                else:
                    # 遠い: ペナルティなし
                    proximity_factor = 0.0

                if proximity_factor > 0:
                    penalty = zone.risk_level * 0.15 * proximity_factor
                    danger_penalty += penalty

                    if zone.risk_type in ("crime", "suspicious_person"):
                        crime_penalty += penalty
                    elif zone.risk_type in ("traffic", "construction"):
                        traffic_penalty += penalty

        danger_penalty = min(danger_penalty, 6.0)
        crime_penalty = min(crime_penalty, 5.0)
        traffic_penalty = min(traffic_penalty, 5.0)

        # --- 時間帯補正 ---
        time_modifier = 0.0
        lighting_modifier = 0.0
        if time_of_day == "night":
            time_modifier = -2.0
            lighting_modifier = -3.0
        elif time_of_day == "evening":
            time_modifier = -1.0
            lighting_modifier = -1.5
        elif time_of_day == "morning":
            time_modifier = 0.5
            lighting_modifier = 0.5

        overall = max(1.0, min(10.0, base_score - danger_penalty + time_modifier))
        traffic_safety = max(1.0, min(10.0, base_score - traffic_penalty))
        crime_safety = max(1.0, min(10.0, base_score - crime_penalty + time_modifier))
        lighting = max(1.0, min(10.0, 8.0 + lighting_modifier))
        community_watch = max(1.0, min(10.0, 7.0))

        return SafetyScoreBreakdown(
            overall=round(overall, 1),
            traffic_safety=round(traffic_safety, 1),
            crime_safety=round(crime_safety, 1),
            lighting=round(lighting, 1),
            community_watch=round(community_watch, 1),
        )

    # ------------------------------------------------------------------ #
    #  ユーティリティ
    # ------------------------------------------------------------------ #

    def _polyline_distance(self, geometry: list[tuple[float, float]]) -> float:
        """ポリライン全体の距離をメートルで計算する"""
        total = 0.0
        for i in range(1, len(geometry)):
            total += self._haversine_distance(
                geometry[i - 1][0], geometry[i - 1][1],
                geometry[i][0], geometry[i][1],
            )
        return total

    async def _get_school(self, school_id: uuid.UUID) -> School | None:
        result = await self.db.execute(
            select(School).where(School.id == school_id)
        )
        return result.scalar_one_or_none()

    async def _get_nearby_danger_zones(
        self,
        origin_lat: float, origin_lng: float,
        dest_lat: float, dest_lng: float,
    ) -> list[RiskFactor]:
        """ルート周辺の危険エリアをPostGIS ST_DWithinで取得する"""
        # ルートの中心点から、ルート全長 + 1km のバッファで検索
        center_lat = (origin_lat + dest_lat) / 2
        center_lng = (origin_lng + dest_lng) / 2
        route_distance = self._haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)
        search_radius = (route_distance / 2) + 1000  # ルート半長 + 1km

        try:
            from app.services.spatial import get_danger_zones_within
            zones = await get_danger_zones_within(
                self.db, center_lat, center_lng, search_radius
            )
        except Exception:
            # PostGIS未対応時のフォールバック
            min_lat = min(origin_lat, dest_lat) - 0.01
            max_lat = max(origin_lat, dest_lat) + 0.01
            min_lng = min(origin_lng, dest_lng) - 0.01
            max_lng = max(origin_lng, dest_lng) + 0.01

            result = await self.db.execute(
                select(DangerZone).where(
                    DangerZone.is_active == True,
                    DangerZone.latitude >= min_lat,
                    DangerZone.latitude <= max_lat,
                    DangerZone.longitude >= min_lng,
                    DangerZone.longitude <= max_lng,
                    (DangerZone.expires_at == None) |
                    (DangerZone.expires_at > datetime.now(timezone.utc)),
                )
            )
            zones = result.scalars().all()

        return [
            RiskFactor(
                latitude=z.latitude,
                longitude=z.longitude,
                risk_level=z.risk_level,
                risk_type=z.risk_type,
                radius_meters=z.radius_meters or 100.0,
            )
            for z in zones
        ]

    @staticmethod
    def _haversine_distance(
        lat1: float, lng1: float, lat2: float, lng2: float
    ) -> float:
        """2点間の距離をハーバーサイン式で計算する（メートル）"""
        R = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

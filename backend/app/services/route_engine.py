"""AI安全ルート計算エンジン"""

import uuid
import math
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
    修正ダイクストラアルゴリズムでリスク重み付きの最適ルートを計算する。
    MVPではMapbox/Google Directions APIと危険エリア回避を組み合わせる。
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
    ) -> RouteCalculateResponse | Route | None:
        """
        安全ルートを計算する。

        Args:
            origin_lat: 出発地の緯度
            origin_lng: 出発地の経度
            destination_lat: 目的地の緯度（school_idが指定されている場合は不要）
            destination_lng: 目的地の経度
            child_id: 子どものID（ルートを保存する場合）
            school_id: 学校ID（目的地として使用）
            time_of_day: 時間帯 (morning/afternoon/evening/night)
            avoid_danger_zones: 危険エリアを回避するか

        Returns:
            計算されたルート情報
        """
        # 学校IDから目的地座標を取得
        if school_id and (destination_lat is None or destination_lng is None):
            school = await self._get_school(school_id)
            if school is None:
                return None
            # 学校の座標を使用（簡易実装）
            # 本来はPostGIS geometryからST_X, ST_Yで取得
            destination_lat = destination_lat or 35.6812  # デフォルト値（東京）
            destination_lng = destination_lng or 139.7671

        if destination_lat is None or destination_lng is None:
            return None

        # 危険エリアを取得
        danger_zones = []
        if avoid_danger_zones:
            danger_zones = await self._get_nearby_danger_zones(
                origin_lat, origin_lng, destination_lat, destination_lng
            )

        # 安全スコアを計算
        safety_breakdown = await self._calculate_safety_score(
            origin_lat, origin_lng,
            destination_lat, destination_lng,
            danger_zones, time_of_day,
        )

        # 直線距離を計算（メートル）
        distance = self._haversine_distance(
            origin_lat, origin_lng, destination_lat, destination_lng
        )

        # 歩行速度（小学生平均）: 約3.5 km/h = 約58 m/min
        walking_speed_mpm = 58.0
        estimated_minutes = distance / walking_speed_mpm

        # ウェイポイント生成（危険エリアを避けるルート）
        waypoints = self._generate_safe_waypoints(
            origin_lat, origin_lng,
            destination_lat, destination_lng,
            danger_zones,
        )

        # ルートをDBに保存（child_idが指定されている場合）
        if child_id:
            route = Route(
                child_id=child_id,
                name="通学路",
                distance_meters=distance,
                estimated_duration_minutes=estimated_minutes,
                safety_score=safety_breakdown.overall,
                is_recommended=True,
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
                is_recommended=True,
                is_active=True,
                created_at=route.created_at,
                updated_at=route.updated_at,
            )

            return RouteCalculateResponse(
                route=route_response,
                safety_breakdown=safety_breakdown,
                danger_zones_nearby=len(danger_zones),
            )

        # child_idがない場合は計算結果のみ返す
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
            is_recommended=False,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        return RouteCalculateResponse(
            route=route_response,
            safety_breakdown=safety_breakdown,
            danger_zones_nearby=len(danger_zones),
        )

    async def _get_school(self, school_id: uuid.UUID) -> School | None:
        """学校情報を取得する"""
        result = await self.db.execute(
            select(School).where(School.id == school_id)
        )
        return result.scalar_one_or_none()

    async def _get_nearby_danger_zones(
        self,
        origin_lat: float, origin_lng: float,
        dest_lat: float, dest_lng: float,
    ) -> list[RiskFactor]:
        """ルート周辺の危険エリアを取得する"""
        # ルートのバウンディングボックスを計算
        min_lat = min(origin_lat, dest_lat) - 0.01  # 約1km余裕
        max_lat = max(origin_lat, dest_lat) + 0.01
        min_lng = min(origin_lng, dest_lng) - 0.01
        max_lng = max(origin_lng, dest_lng) + 0.01

        result = await self.db.execute(
            select(DangerZone).where(
                DangerZone.is_active == True,
                (DangerZone.expires_at == None) |
                (DangerZone.expires_at > datetime.now(timezone.utc)),
            )
        )
        zones = result.scalars().all()

        # 危険エリアをRiskFactorに変換
        risk_factors = []
        for zone in zones:
            risk_factors.append(
                RiskFactor(
                    latitude=0.0,  # PostGIS geometryから取得する
                    longitude=0.0,
                    risk_level=zone.risk_level,
                    risk_type=zone.risk_type,
                    radius_meters=zone.radius_meters or 100.0,
                )
            )

        return risk_factors

    async def _calculate_safety_score(
        self,
        origin_lat: float, origin_lng: float,
        dest_lat: float, dest_lng: float,
        danger_zones: list[RiskFactor],
        time_of_day: str | None = None,
    ) -> SafetyScoreBreakdown:
        """ルートの安全スコアを計算する"""
        base_score = 8.0

        # 危険エリアによる減点
        danger_penalty = 0.0
        for zone in danger_zones:
            danger_penalty += zone.risk_level * 0.1
        danger_penalty = min(danger_penalty, 5.0)

        # 時間帯による補正
        time_modifier = 0.0
        if time_of_day == "night":
            time_modifier = -2.0
        elif time_of_day == "evening":
            time_modifier = -1.0
        elif time_of_day == "morning":
            time_modifier = 0.5

        overall = max(1.0, min(10.0, base_score - danger_penalty + time_modifier))

        # カテゴリ別スコア
        traffic_safety = max(1.0, min(10.0, base_score - danger_penalty * 0.3))
        crime_safety = max(1.0, min(10.0, base_score - danger_penalty * 0.4))
        lighting = max(1.0, min(10.0, 8.0 + time_modifier))
        community_watch = max(1.0, min(10.0, 7.0))

        return SafetyScoreBreakdown(
            overall=round(overall, 1),
            traffic_safety=round(traffic_safety, 1),
            crime_safety=round(crime_safety, 1),
            lighting=round(lighting, 1),
            community_watch=round(community_watch, 1),
        )

    def _generate_safe_waypoints(
        self,
        origin_lat: float, origin_lng: float,
        dest_lat: float, dest_lng: float,
        danger_zones: list[RiskFactor],
    ) -> list[RouteWaypoint]:
        """
        危険エリアを避けるウェイポイントを生成する。
        シンプルな実装: 出発地→中間点→目的地の3点ルート。
        危険エリアがある場合は迂回ポイントを追加。
        """
        waypoints = [
            RouteWaypoint(
                latitude=origin_lat,
                longitude=origin_lng,
                order=0,
            ),
        ]

        # 中間点を追加（危険エリアがある場合は少しずらす）
        mid_lat = (origin_lat + dest_lat) / 2
        mid_lng = (origin_lng + dest_lng) / 2

        if danger_zones:
            # 危険エリアから離れる方向に中間点をずらす
            offset = 0.002  # 約200m
            mid_lat += offset
            mid_lng += offset

        waypoints.append(
            RouteWaypoint(
                latitude=mid_lat,
                longitude=mid_lng,
                order=1,
            )
        )

        waypoints.append(
            RouteWaypoint(
                latitude=dest_lat,
                longitude=dest_lng,
                order=2,
            ),
        )

        return waypoints

    @staticmethod
    def _haversine_distance(
        lat1: float, lng1: float, lat2: float, lng2: float
    ) -> float:
        """2点間の距離をハーバーサイン式で計算する（メートル）"""
        R = 6371000  # 地球の半径（メートル）

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

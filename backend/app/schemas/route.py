"""安全ルートスキーマ"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class RoutePoint(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class RouteCalculateRequest(BaseModel):
    """ルート計算リクエスト"""
    origin: RoutePoint
    destination: RoutePoint
    child_id: uuid.UUID | None = None
    time_of_day: str | None = Field(
        None, description="時間帯: morning, afternoon, evening, night"
    )
    avoid_danger_zones: bool = True


class RouteWaypoint(BaseModel):
    latitude: float
    longitude: float
    order: int


class RouteResponse(BaseModel):
    id: uuid.UUID
    child_id: uuid.UUID
    name: str
    origin: RoutePoint | None = None
    destination: RoutePoint | None = None
    waypoints: list[RouteWaypoint] = []
    distance_meters: float | None = None
    estimated_duration_minutes: float | None = None
    safety_score: float
    is_recommended: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RouteListResponse(BaseModel):
    routes: list[RouteResponse]
    total: int


class SafetyScoreBreakdown(BaseModel):
    """安全スコアの内訳"""
    overall: float = Field(..., ge=0, le=10)
    traffic_safety: float = Field(..., ge=0, le=10)
    crime_safety: float = Field(..., ge=0, le=10)
    lighting: float = Field(..., ge=0, le=10)
    community_watch: float = Field(..., ge=0, le=10)


class RouteCalculateResponse(BaseModel):
    """ルート計算レスポンス"""
    route: RouteResponse
    safety_breakdown: SafetyScoreBreakdown
    alternative_routes: list[RouteResponse] = []
    danger_zones_nearby: int = 0

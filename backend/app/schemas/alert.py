"""アラートスキーマ"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    id: uuid.UUID
    child_id: uuid.UUID
    user_id: uuid.UUID
    alert_type: str
    severity: str
    title: str
    message: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_read: bool
    is_resolved: bool
    resolved_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse]
    total: int
    unread_count: int


class AlertUnreadCountResponse(BaseModel):
    unread_count: int


class AlertMarkReadRequest(BaseModel):
    """アラート既読リクエスト"""
    alert_ids: list[uuid.UUID] | None = Field(
        None, description="既読にするアラートID（Noneで全件既読）"
    )


class DangerZoneCreate(BaseModel):
    """危険エリア報告リクエスト"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_meters: float = Field(100, ge=10, le=5000, description="影響半径 (メートル)")
    risk_level: int = Field(5, ge=1, le=10, description="リスクレベル")
    risk_type: str = Field("other", description="リスク種別")
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None


class DangerZoneResponse(BaseModel):
    id: uuid.UUID
    latitude: float | None = None
    longitude: float | None = None
    radius_meters: float | None = None
    risk_level: int
    risk_type: str
    title: str
    description: str | None = None
    source: str
    reported_at: datetime
    expires_at: datetime | None = None
    is_active: bool
    verified: bool

    model_config = {"from_attributes": True}


class DangerZoneListResponse(BaseModel):
    danger_zones: list[DangerZoneResponse]
    total: int


class HeatmapPoint(BaseModel):
    latitude: float
    longitude: float
    weight: float = Field(..., ge=0, le=1, description="重み (0-1)")
    risk_type: str | None = None


class HeatmapResponse(BaseModel):
    """安全ヒートマップデータ"""
    points: list[HeatmapPoint]
    center_latitude: float
    center_longitude: float
    radius_meters: float

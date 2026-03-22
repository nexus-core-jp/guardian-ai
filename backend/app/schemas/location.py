"""位置情報スキーマ"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class LocationCreate(BaseModel):
    """位置情報記録リクエスト"""

    child_id: uuid.UUID
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: float | None = None
    speed: float | None = Field(None, ge=0, description="移動速度 (m/s)")
    accuracy: float | None = Field(None, ge=0, description="精度 (メートル)")
    heading: float | None = Field(None, ge=0, le=360, description="方位角")
    source: str = Field("gps_device", description="取得元: gps_device, app, manual")
    battery_level: float | None = Field(
        None, ge=0, le=100, description="バッテリー残量 (%)"
    )
    timestamp: datetime | None = None


class LocationResponse(BaseModel):
    id: uuid.UUID
    child_id: uuid.UUID
    latitude: float
    longitude: float
    altitude: float | None = None
    speed: float | None = None
    accuracy: float | None = None
    heading: float | None = None
    source: str
    battery_level: float | None = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class LocationHistoryRequest(BaseModel):
    """位置情報履歴リクエスト"""

    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = Field(100, ge=1, le=1000)


class LocationHistoryResponse(BaseModel):
    locations: list[LocationResponse]
    total: int
    child_id: uuid.UUID


class LatestLocationResponse(BaseModel):
    """最新位置情報"""

    child_id: uuid.UUID
    child_name: str
    location: LocationResponse | None = None
    last_updated: datetime | None = None

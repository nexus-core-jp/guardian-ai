"""子どもスキーマ"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class SchoolBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    address: str | None = None
    prefecture: str | None = None
    city: str | None = None


class SchoolCreate(SchoolBase):
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)


class SchoolResponse(SchoolBase):
    id: uuid.UUID
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChildBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="子どもの名前")
    grade: int | None = Field(None, ge=1, le=6, description="学年 (1-6)")


class ChildCreate(ChildBase):
    school_id: uuid.UUID | None = Field(None, description="学校ID")
    device_id: str | None = Field(None, description="GPSデバイスID")


class ChildUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    grade: int | None = Field(None, ge=1, le=6)
    school_id: uuid.UUID | None = None
    device_id: str | None = None
    avatar_url: str | None = None


class ChildResponse(ChildBase):
    id: uuid.UUID
    user_id: uuid.UUID
    school_id: uuid.UUID | None = None
    school: SchoolResponse | None = None
    device_id: str | None = None
    avatar_url: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChildListResponse(BaseModel):
    children: list[ChildResponse]
    total: int

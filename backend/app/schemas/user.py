"""ユーザースキーマ"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="保護者名")
    email: str | None = Field(None, max_length=255, description="メールアドレス")


class UserCreate(UserBase):
    line_id: str | None = Field(None, description="LINE ユーザーID")


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    email: str | None = Field(None, max_length=255)
    avatar_url: str | None = None
    fcm_token: str | None = None
    home_latitude: float | None = None
    home_longitude: float | None = None


class UserResponse(UserBase):
    id: uuid.UUID
    line_id: str | None = None
    avatar_url: str | None = None
    home_latitude: float | None = None
    home_longitude: float | None = None
    onboarding_completed: bool = False
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OnboardingRequest(BaseModel):
    """初期セットアップリクエスト"""
    home_latitude: float = Field(..., ge=-90, le=90, description="自宅の緯度")
    home_longitude: float = Field(..., ge=-180, le=180, description="自宅の経度")
    school_id: uuid.UUID | None = Field(None, description="学校ID")
    school_name: str | None = Field(None, description="学校名（新規登録用）")
    child_name: str = Field(..., min_length=1, max_length=100, description="子どもの名前")
    child_grade: int | None = Field(None, ge=1, le=6, description="学年")


class OnboardingResponse(BaseModel):
    """初期セットアップレスポンス"""
    user: UserResponse
    child_id: uuid.UUID
    recommended_route_id: uuid.UUID | None = None
    message: str = "セットアップが完了しました"


class TokenResponse(BaseModel):
    """認証トークンレスポンス"""
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: UserResponse


class LINELoginRequest(BaseModel):
    """LINE ログインリクエスト"""
    code: str = Field(..., description="LINE認証コード")
    state: str | None = Field(None, description="CSRFトークン")


class RefreshTokenRequest(BaseModel):
    """トークンリフレッシュリクエスト"""
    refresh_token: str = Field(..., description="リフレッシュトークン")


class RefreshTokenResponse(BaseModel):
    """トークンリフレッシュレスポンス"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

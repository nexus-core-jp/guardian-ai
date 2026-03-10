"""設定エンドポイント"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse
from app.api.deps import get_current_user

router = APIRouter()


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    email: str | None = Field(None, max_length=255)


class HomeLocationUpdateRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: str = Field(..., min_length=1, max_length=500)


@router.patch("/profile", response_model=UserResponse, summary="プロフィール更新")
async def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """保護者プロフィール（名前・メール）を更新する"""
    if data.name is not None:
        current_user.name = data.name
    if data.email is not None:
        current_user.email = data.email
    await db.flush()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.patch("/home-location", summary="自宅位置更新")
async def update_home_location(
    data: HomeLocationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """自宅の位置情報を更新する"""
    current_user.home_latitude = data.latitude
    current_user.home_longitude = data.longitude
    await db.flush()
    return {
        "status": "ok",
        "latitude": data.latitude,
        "longitude": data.longitude,
        "address": data.address,
    }


@router.delete("/account", status_code=status.HTTP_200_OK, summary="アカウント削除")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    アカウントを論理削除する。
    ユーザーを無効化し、個人情報を匿名化する。
    """
    current_user.is_active = False
    current_user.name = "退会ユーザー"
    current_user.email = None
    current_user.line_id = None
    current_user.apple_id = None
    current_user.google_id = None
    current_user.avatar_url = None
    current_user.fcm_token = None
    await db.flush()
    return {"status": "ok", "message": "アカウントが削除されました"}

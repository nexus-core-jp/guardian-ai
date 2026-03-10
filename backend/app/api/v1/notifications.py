"""通知設定エンドポイント"""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.notification_preferences import NotificationPreferences
from app.api.deps import get_current_user

router = APIRouter()


class NotificationPreferencesResponse(BaseModel):
    route_deviation: bool = True
    danger_zone: bool = True
    arrival: bool = True
    departure: bool = True
    community_reports: bool = True

    model_config = {"from_attributes": True}


class NotificationPreferencesUpdate(BaseModel):
    route_deviation: bool | None = None
    danger_zone: bool | None = None
    arrival: bool | None = None
    departure: bool | None = None
    community_reports: bool | None = None


@router.get("/preferences", response_model=NotificationPreferencesResponse, summary="通知設定取得")
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """現在の通知設定を取得する"""
    result = await db.execute(
        select(NotificationPreferences).where(
            NotificationPreferences.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()

    if prefs is None:
        # デフォルト値を返す
        return NotificationPreferencesResponse()

    return NotificationPreferencesResponse.model_validate(prefs)


@router.patch("/preferences", response_model=NotificationPreferencesResponse, summary="通知設定更新")
async def update_preferences(
    data: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """通知設定を更新する"""
    result = await db.execute(
        select(NotificationPreferences).where(
            NotificationPreferences.user_id == current_user.id
        )
    )
    prefs = result.scalar_one_or_none()

    if prefs is None:
        prefs = NotificationPreferences(user_id=current_user.id)
        db.add(prefs)

    update_data = data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(prefs, field, value)

    await db.flush()
    await db.refresh(prefs)
    return NotificationPreferencesResponse.model_validate(prefs)

"""アラートエンドポイント"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.alert import Alert
from app.schemas.alert import (
    AlertResponse,
    AlertListResponse,
    AlertUnreadCountResponse,
)
from app.api.deps import get_current_user

router = APIRouter()


@router.get("", response_model=AlertListResponse, summary="アラート一覧取得")
async def list_alerts(
    severity: str | None = Query(None, description="重要度フィルター"),
    alert_type: str | None = Query(None, description="種別フィルター"),
    is_read: bool | None = Query(None, description="既読フィルター"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """現在のユーザーのアラート一覧を取得する"""
    query = select(Alert).where(Alert.user_id == current_user.id)

    if severity:
        query = query.where(Alert.severity == severity)
    if alert_type:
        query = query.where(Alert.alert_type == alert_type)
    if is_read is not None:
        query = query.where(Alert.is_read == is_read)

    # 総件数（同じフィルターを適用）
    count_query = (
        select(func.count()).select_from(Alert).where(Alert.user_id == current_user.id)
    )
    if severity:
        count_query = count_query.where(Alert.severity == severity)
    if alert_type:
        count_query = count_query.where(Alert.alert_type == alert_type)
    if is_read is not None:
        count_query = count_query.where(Alert.is_read == is_read)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # 未読件数
    unread_query = (
        select(func.count())
        .select_from(Alert)
        .where(Alert.user_id == current_user.id, Alert.is_read == False)
    )
    unread_result = await db.execute(unread_query)
    unread_count = unread_result.scalar() or 0

    # アラート取得
    query = query.order_by(desc(Alert.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    alerts = result.scalars().all()

    return AlertListResponse(
        alerts=[AlertResponse.model_validate(a) for a in alerts],
        total=total,
        unread_count=unread_count,
    )


@router.get(
    "/unread", response_model=AlertUnreadCountResponse, summary="未読アラート件数"
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """未読アラートの件数を取得する"""
    result = await db.execute(
        select(func.count())
        .select_from(Alert)
        .where(
            Alert.user_id == current_user.id,
            Alert.is_read == False,
        )
    )
    count = result.scalar() or 0

    return AlertUnreadCountResponse(unread_count=count)


@router.put(
    "/{alert_id}/read", response_model=AlertResponse, summary="アラートを既読にする"
)
async def mark_alert_read(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """指定したアラートを既読にする"""
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.user_id == current_user.id,
        )
    )
    alert = result.scalar_one_or_none()

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="アラートが見つかりません",
        )

    alert.is_read = True
    await db.flush()
    await db.refresh(alert)

    return AlertResponse.model_validate(alert)


@router.put(
    "/{alert_id}/resolve",
    response_model=AlertResponse,
    summary="アラートを解決済みにする",
)
async def resolve_alert(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """指定したアラートを解決済みにする"""
    from datetime import datetime, timezone

    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.user_id == current_user.id,
        )
    )
    alert = result.scalar_one_or_none()

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="アラートが見つかりません",
        )

    alert.is_resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(alert)

    return AlertResponse.model_validate(alert)


@router.put(
    "/read-all",
    response_model=AlertUnreadCountResponse,
    summary="全アラートを既読にする",
)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """全ての未読アラートを既読にする"""
    from sqlalchemy import update

    await db.execute(
        update(Alert)
        .where(Alert.user_id == current_user.id, Alert.is_read == False)
        .values(is_read=True)
    )
    await db.flush()

    return AlertUnreadCountResponse(unread_count=0)

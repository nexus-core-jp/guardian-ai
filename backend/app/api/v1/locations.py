"""位置情報トラッキングエンドポイント"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.child import Child
from app.models.location import Location
from app.schemas.location import (
    LocationCreate,
    LocationResponse,
    LocationHistoryResponse,
    LatestLocationResponse,
)
from app.api.deps import get_current_user
from app.services.anomaly_detector import AnomalyDetector
from app.services.alert_service import AlertService
from app.services.websocket_manager import ws_manager

router = APIRouter()


async def _verify_child_ownership(
    child_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> Child:
    """子どもが現在のユーザーに紐づいているか確認する"""
    result = await db.execute(
        select(Child).where(Child.id == child_id, Child.user_id == user_id)
    )
    child = result.scalar_one_or_none()
    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="子どもの情報が見つかりません",
        )
    return child


@router.post(
    "", response_model=LocationResponse, status_code=status.HTTP_201_CREATED,
    summary="位置情報を記録",
)
async def record_location(
    data: LocationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    GPSデバイスまたはアプリから位置情報を記録する。
    異常検知も同時に実行し、必要に応じてアラートを生成する。
    """
    _child = await _verify_child_ownership(data.child_id, current_user.id, db)

    # 位置情報を保存
    location = Location(
        child_id=data.child_id,
        latitude=data.latitude,
        longitude=data.longitude,
        altitude=data.altitude,
        speed=data.speed,
        accuracy=data.accuracy,
        heading=data.heading,
        source=data.source,
        battery_level=data.battery_level,
        timestamp=data.timestamp or datetime.now(timezone.utc),
    )
    db.add(location)
    await db.flush()

    # 異常検知を非同期で実行
    try:
        detector = AnomalyDetector(db)
        anomaly = await detector.detect_anomaly(
            child_id=data.child_id,
            latitude=data.latitude,
            longitude=data.longitude,
            speed=data.speed,
        )

        if anomaly and anomaly.is_anomalous:
            alert_service = AlertService(db)
            await alert_service.create_alert_from_anomaly(
                child_id=data.child_id,
                user_id=current_user.id,
                anomaly=anomaly,
                latitude=data.latitude,
                longitude=data.longitude,
            )
    except Exception:
        # 異常検知の失敗は位置情報の記録には影響させない
        pass

    await db.refresh(location)

    # WebSocketでリアルタイム配信
    location_response = LocationResponse.model_validate(location)
    try:
        await ws_manager.broadcast_location(
            child_id=data.child_id,
            location_data=location_response.model_dump(mode="json"),
        )
    except Exception:
        pass  # WebSocket配信失敗はAPI応答に影響させない

    return location_response


@router.get(
    "/{child_id}/latest", response_model=LatestLocationResponse,
    summary="最新位置情報を取得",
)
async def get_latest_location(
    child_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """子どもの最新の位置情報を取得する"""
    child = await _verify_child_ownership(child_id, current_user.id, db)

    result = await db.execute(
        select(Location)
        .where(Location.child_id == child_id)
        .order_by(desc(Location.timestamp))
        .limit(1)
    )
    location = result.scalar_one_or_none()

    return LatestLocationResponse(
        child_id=child_id,
        child_name=child.name,
        location=LocationResponse.model_validate(location) if location else None,
        last_updated=location.timestamp if location else None,
    )


@router.get(
    "/{child_id}/history", response_model=LocationHistoryResponse,
    summary="位置情報履歴を取得",
)
async def get_location_history(
    child_id: uuid.UUID,
    start_time: datetime | None = Query(None, description="開始時刻"),
    end_time: datetime | None = Query(None, description="終了時刻"),
    limit: int = Query(100, ge=1, le=1000, description="取得件数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """子どもの位置情報履歴を取得する"""
    await _verify_child_ownership(child_id, current_user.id, db)

    query = select(Location).where(Location.child_id == child_id)

    if start_time:
        query = query.where(Location.timestamp >= start_time)
    if end_time:
        query = query.where(Location.timestamp <= end_time)

    query = query.order_by(desc(Location.timestamp)).limit(limit)

    result = await db.execute(query)
    locations = result.scalars().all()

    # 総件数
    count_query = select(func.count()).select_from(Location).where(
        Location.child_id == child_id
    )
    if start_time:
        count_query = count_query.where(Location.timestamp >= start_time)
    if end_time:
        count_query = count_query.where(Location.timestamp <= end_time)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return LocationHistoryResponse(
        locations=[LocationResponse.model_validate(loc) for loc in locations],
        total=total,
        child_id=child_id,
    )

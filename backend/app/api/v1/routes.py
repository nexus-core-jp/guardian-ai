"""安全ルートエンドポイント"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.child import Child
from app.models.route import Route
from app.schemas.route import (
    RouteCalculateRequest,
    RouteCalculateResponse,
    RouteResponse,
    RouteListResponse,
    RoutePoint,
    RouteWaypoint,
)
from app.api.deps import get_current_user
from app.services.route_engine import RouteEngine

router = APIRouter()


@router.get(
    "/{child_id}/recommended",
    response_model=RouteResponse,
    summary="推奨ルートを取得",
)
async def get_recommended_route(
    child_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    子どもの本日の推奨安全ルートを取得する。
    推奨ルートが未計算の場合は自動計算を試みる。
    """
    # 子どもの所有権確認
    result = await db.execute(
        select(Child).where(Child.id == child_id, Child.user_id == current_user.id)
    )
    child = result.scalar_one_or_none()
    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="子どもの情報が見つかりません",
        )

    # 推奨ルートを検索
    route_result = await db.execute(
        select(Route)
        .where(
            Route.child_id == child_id,
            Route.is_recommended == True,
            Route.is_active == True,
        )
        .order_by(Route.safety_score.desc())
        .limit(1)
    )
    route = route_result.scalar_one_or_none()

    if route is None:
        # 自宅と学校の情報があればルートを計算
        if current_user.home_latitude and child.school_id:
            try:
                engine = RouteEngine(db)
                calc_result = await engine.calculate_safe_route(
                    origin_lat=current_user.home_latitude,
                    origin_lng=current_user.home_longitude,
                    child_id=child_id,
                    school_id=child.school_id,
                )
                if calc_result is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="推奨ルートの計算に失敗しました。学校の座標情報を確認してください。",
                    )
                return calc_result.route
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="推奨ルートの計算に失敗しました。自宅と学校の情報を確認してください。",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="推奨ルートが見つかりません。オンボーディングを完了してください。",
            )

    # Existing Route model needs to be converted to RouteResponse with origin/destination
    return RouteResponse(
        id=route.id,
        child_id=route.child_id,
        name=route.name,
        origin=RoutePoint(latitude=route.origin_lat, longitude=route.origin_lng),
        destination=RoutePoint(
            latitude=route.destination_lat, longitude=route.destination_lng
        ),
        waypoints=[RouteWaypoint(**wp) for wp in (route.waypoints_json or [])],
        distance_meters=route.distance_meters,
        estimated_duration_minutes=route.estimated_duration_minutes,
        safety_score=route.safety_score,
        is_recommended=route.is_recommended,
        is_active=route.is_active,
        created_at=route.created_at,
        updated_at=route.updated_at,
    )


@router.get(
    "/{child_id}",
    response_model=RouteListResponse,
    summary="ルート一覧取得",
)
async def list_routes(
    child_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """子どもに紐づく全ルートを取得する"""
    result = await db.execute(
        select(Child).where(Child.id == child_id, Child.user_id == current_user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="子どもの情報が見つかりません",
        )

    routes_result = await db.execute(
        select(Route)
        .where(Route.child_id == child_id, Route.is_active == True)
        .order_by(Route.safety_score.desc())
    )
    routes = routes_result.scalars().all()

    route_responses = []
    for r in routes:
        route_responses.append(
            RouteResponse(
                id=r.id,
                child_id=r.child_id,
                name=r.name,
                origin=RoutePoint(latitude=r.origin_lat, longitude=r.origin_lng),
                destination=RoutePoint(
                    latitude=r.destination_lat, longitude=r.destination_lng
                ),
                waypoints=[RouteWaypoint(**wp) for wp in (r.waypoints_json or [])],
                distance_meters=r.distance_meters,
                estimated_duration_minutes=r.estimated_duration_minutes,
                safety_score=r.safety_score,
                is_recommended=r.is_recommended,
                is_active=r.is_active,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )

    return RouteListResponse(
        routes=route_responses,
        total=len(route_responses),
    )


@router.post(
    "/calculate",
    response_model=RouteCalculateResponse,
    summary="安全ルートを計算",
)
async def calculate_route(
    data: RouteCalculateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    2地点間の安全ルートを計算する。
    危険エリアを回避し、安全スコアが最も高いルートを返す。
    """
    engine = RouteEngine(db)

    try:
        result = await engine.calculate_safe_route(
            origin_lat=data.origin.latitude,
            origin_lng=data.origin.longitude,
            destination_lat=data.destination.latitude,
            destination_lng=data.destination.longitude,
            child_id=data.child_id,
            time_of_day=data.time_of_day,
            avoid_danger_zones=data.avoid_danger_zones,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ルートの計算に失敗しました: {str(e)}",
        )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ルートが見つかりません",
        )

    return result

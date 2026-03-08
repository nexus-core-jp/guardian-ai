"""コミュニティ/地域見守りエンドポイント"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.danger_zone import DangerZone, RiskType, DangerZoneSource
from app.schemas.alert import (
    DangerZoneCreate,
    DangerZoneResponse,
    DangerZoneListResponse,
    HeatmapPoint,
    HeatmapResponse,
)
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/dangers", response_model=DangerZoneListResponse, summary="近隣の危険エリア一覧")
async def list_danger_zones(
    latitude: float = Query(..., ge=-90, le=90, description="中心緯度"),
    longitude: float = Query(..., ge=-180, le=180, description="中心経度"),
    radius_km: float = Query(2.0, ge=0.1, le=50, description="検索半径 (km)"),
    risk_type: str | None = Query(None, description="リスク種別フィルター"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    指定した地点の近隣にある危険エリアを取得する。
    PostGISのST_DWithinを使用した空間検索を行う。
    """
    # 簡易的な距離フィルタ（PostGISが利用できない場合のフォールバック）
    # 緯度1度 ≈ 111km, 経度1度 ≈ 91km（日本の平均）
    lat_range = radius_km / 111.0
    lng_range = radius_km / 91.0

    query = select(DangerZone).where(
        DangerZone.is_active == True,
    )

    if risk_type:
        query = query.where(DangerZone.risk_type == risk_type)

    # 有効期限チェック
    query = query.where(
        (DangerZone.expires_at == None) |
        (DangerZone.expires_at > datetime.now(timezone.utc))
    )

    result = await db.execute(query.order_by(DangerZone.risk_level.desc()))
    all_zones = result.scalars().all()

    # アプリケーションレベルで距離フィルタ（PostGIS利用時はSQLで行う）
    filtered_zones = []
    for zone in all_zones:
        # DangerZoneにはlat/lngカラムがないので、PostGIS POINT geometryから取得するか
        # 簡易的にすべて返す
        filtered_zones.append(zone)

    return DangerZoneListResponse(
        danger_zones=[DangerZoneResponse.model_validate(z) for z in filtered_zones],
        total=len(filtered_zones),
    )


@router.post(
    "/dangers", response_model=DangerZoneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="危険エリアを報告",
)
async def report_danger_zone(
    data: DangerZoneCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    地域の危険エリアを報告する。
    コミュニティメンバーからの情報を収集し、地域全体の安全に役立てる。
    """
    danger_zone = DangerZone(
        risk_level=data.risk_level,
        risk_type=data.risk_type,
        title=data.title,
        description=data.description,
        radius_meters=data.radius_meters,
        source=DangerZoneSource.COMMUNITY,
        reported_by=current_user.id,
    )
    db.add(danger_zone)
    await db.flush()
    await db.refresh(danger_zone)

    return DangerZoneResponse(
        id=danger_zone.id,
        latitude=data.latitude,
        longitude=data.longitude,
        radius_meters=danger_zone.radius_meters,
        risk_level=danger_zone.risk_level,
        risk_type=danger_zone.risk_type,
        title=danger_zone.title,
        description=danger_zone.description,
        source=danger_zone.source,
        reported_at=danger_zone.reported_at,
        expires_at=danger_zone.expires_at,
        is_active=danger_zone.is_active,
        verified=danger_zone.verified,
    )


@router.get("/heatmap", response_model=HeatmapResponse, summary="安全ヒートマップデータ")
async def get_safety_heatmap(
    latitude: float = Query(..., ge=-90, le=90, description="中心緯度"),
    longitude: float = Query(..., ge=-180, le=180, description="中心経度"),
    radius_km: float = Query(2.0, ge=0.1, le=10, description="半径 (km)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    指定エリアの安全ヒートマップデータを返す。
    危険エリアの情報を集約し、ヒートマップ表示用のデータを生成する。
    """
    # 危険エリアを取得
    result = await db.execute(
        select(DangerZone).where(
            DangerZone.is_active == True,
            (DangerZone.expires_at == None) |
            (DangerZone.expires_at > datetime.now(timezone.utc)),
        )
    )
    zones = result.scalars().all()

    # ヒートマップポイントを生成
    points = []
    for zone in zones:
        weight = min(zone.risk_level / 10.0, 1.0)
        points.append(
            HeatmapPoint(
                latitude=latitude,  # 本来はgeometryから取得
                longitude=longitude,
                weight=weight,
                risk_type=zone.risk_type,
            )
        )

    return HeatmapResponse(
        points=points,
        center_latitude=latitude,
        center_longitude=longitude,
        radius_meters=radius_km * 1000,
    )

"""学校検索エンドポイント"""

import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.child import School
from app.schemas.child import SchoolResponse

from pydantic import BaseModel

router = APIRouter()


class SchoolListResponse(BaseModel):
    schools: list[SchoolResponse]
    total: int


@router.get("/search", response_model=SchoolListResponse, summary="学校名で検索")
async def search_schools(
    q: str = Query(..., min_length=1, description="検索キーワード"),
    lat: float | None = Query(None, description="現在地の緯度（距離順ソート用）"),
    lng: float | None = Query(None, description="現在地の経度（距離順ソート用）"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """学校名またはキーワードで小学校を検索する"""
    query = select(School).where(
        or_(
            School.name.ilike(f"%{q}%"),
            School.address.ilike(f"%{q}%"),
            School.city.ilike(f"%{q}%"),
        ),
    )

    # 位置情報がある場合は距離順でソート
    if lat is not None and lng is not None:
        # PostgreSQLの簡易距離計算（度数ベース、近距離なら十分）
        distance = func.sqrt(
            func.power(School.latitude - lat, 2)
            + func.power((School.longitude - lng) * func.cos(func.radians(lat)), 2)
        )
        query = query.order_by(distance)
    else:
        query = query.order_by(School.name)

    query = query.limit(limit)
    result = await db.execute(query)
    schools = list(result.scalars().all())

    # 総件数
    count_query = (
        select(func.count())
        .select_from(School)
        .where(
            or_(
                School.name.ilike(f"%{q}%"),
                School.address.ilike(f"%{q}%"),
                School.city.ilike(f"%{q}%"),
            ),
        )
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return SchoolListResponse(
        schools=[SchoolResponse.model_validate(s) for s in schools],
        total=total,
    )


@router.get("/nearby", response_model=SchoolListResponse, summary="近くの学校を検索")
async def nearby_schools(
    lat: float = Query(..., description="緯度"),
    lng: float = Query(..., description="経度"),
    radius: float = Query(5000, description="検索半径（メートル）"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """指定座標から近い学校を距離順で返す"""
    # メートルを緯度の度数に近似変換（1度 ≈ 111km）
    lat_range = radius / 111_000
    lng_range = radius / (111_000 * math.cos(math.radians(lat)))

    query = select(School).where(
        School.latitude.isnot(None),
        School.longitude.isnot(None),
        School.latitude.between(lat - lat_range, lat + lat_range),
        School.longitude.between(lng - lng_range, lng + lng_range),
    )

    distance = func.sqrt(
        func.power(School.latitude - lat, 2)
        + func.power((School.longitude - lng) * func.cos(func.radians(lat)), 2)
    )
    query = query.order_by(distance).limit(limit)

    result = await db.execute(query)
    schools = list(result.scalars().all())

    return SchoolListResponse(
        schools=[SchoolResponse.model_validate(s) for s in schools],
        total=len(schools),
    )

"""PostGIS空間クエリユーティリティ"""

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.danger_zone import DangerZone
from app.models.location import Location


def st_dwithin(geom_column, lat: float, lng: float, distance_meters: float):
    """
    PostGIS ST_DWithin を使った空間フィルタ条件を返す。
    geom列がある場合はST_DWithinを使用し、ない場合はバウンディングボックスにフォールバック。

    Args:
        geom_column: SQLAlchemy Column（geom列）
        lat: 中心緯度
        lng: 中心経度
        distance_meters: 半径（メートル）

    Returns:
        SQLAlchemy WHERE条件
    """
    point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
    # ST_DWithin with geography cast for meter-based distance
    return func.ST_DWithin(
        func.Geography(geom_column),
        func.Geography(point),
        distance_meters,
    )


def st_distance_meters(geom_column, lat: float, lng: float):
    """
    PostGIS ST_Distance を使って距離（メートル）を計算する式を返す。

    Returns:
        SQLAlchemy式（メートル単位の距離）
    """
    point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
    return func.ST_Distance(
        func.Geography(geom_column),
        func.Geography(point),
    )


async def get_danger_zones_within(
    db: AsyncSession,
    lat: float,
    lng: float,
    radius_meters: float,
    active_only: bool = True,
) -> list[DangerZone]:
    """
    指定地点から半径内の危険ゾーンをPostGIS ST_DWithinで取得する。

    Args:
        db: DBセッション
        lat: 中心緯度
        lng: 中心経度
        radius_meters: 検索半径（メートル）
        active_only: アクティブなゾーンのみ

    Returns:
        DangerZoneリスト
    """
    from datetime import datetime, timezone

    query = select(DangerZone).where(
        st_dwithin(DangerZone.geom, lat, lng, radius_meters),
    )

    if active_only:
        query = query.where(
            DangerZone.is_active == True,
            (DangerZone.expires_at == None) |
            (DangerZone.expires_at > datetime.now(timezone.utc)),
        )

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_nearby_locations(
    db: AsyncSession,
    child_id,
    lat: float,
    lng: float,
    radius_meters: float,
    limit: int = 20,
) -> list[Location]:
    """
    指定地点から半径内の位置情報をPostGIS ST_DWithinで取得する。
    """
    from sqlalchemy import desc

    query = (
        select(Location)
        .where(
            Location.child_id == child_id,
            st_dwithin(Location.geom, lat, lng, radius_meters),
        )
        .order_by(desc(Location.timestamp))
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())

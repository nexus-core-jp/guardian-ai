"""コミュニティ/地域見守りエンドポイント"""

from datetime import datetime, timezone, timedelta
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.danger_zone import DangerZone, DangerZoneSource
from app.schemas.alert import (
    DangerZoneCreate,
    DangerZoneResponse,
    DangerZoneListResponse,
    HeatmapPoint,
    HeatmapResponse,
)
from app.api.deps import get_current_user

router = APIRouter()


# ── Local News schemas ──────────────────────────────────────────────


class NewsType(str, Enum):
    suspicious_person = "suspicious_person"
    traffic_accident = "traffic_accident"
    construction = "construction"
    weather = "weather"
    event = "event"


class LocalNewsItem(BaseModel):
    id: str
    type: NewsType
    title: str
    summary: str
    source: str
    published_at: datetime
    location: str | None = None


class LocalNewsListResponse(BaseModel):
    news: list[LocalNewsItem]
    total: int


# ── Hardcoded sample news (to be replaced by real data sources) ─────


def _build_sample_news() -> list[dict]:
    """Generate sample news with fresh timestamps relative to now."""
    now = datetime.now(timezone.utc)
    return [
        {
            "id": "news-001",
            "type": "suspicious_person",
            "title": "不審者目撃情報 - 渋谷区神宮前付近",
            "summary": "本日15時頃、小学生に声をかける不審な男性が目撃されました。紺色のジャケット、30代くらい。警察に通報済み。",
            "source": "警視庁犯罪抑止対策本部",
            "published_at": (now - timedelta(hours=2)).isoformat(),
            "location": "渋谷区神宮前3丁目",
            "lat": 35.6695,
            "lng": 139.7080,
        },
        {
            "id": "news-002",
            "type": "traffic_accident",
            "title": "通学路で交通事故発生 - 明治通り交差点",
            "summary": "自転車と歩行者の接触事故が発生。該当交差点は一時通行止め。迂回ルートをご利用ください。",
            "source": "警視庁交通情報",
            "published_at": (now - timedelta(hours=5)).isoformat(),
            "location": "渋谷区千駄ヶ谷1丁目",
            "lat": 35.6801,
            "lng": 139.7114,
        },
        {
            "id": "news-003",
            "type": "construction",
            "title": "道路工事のお知らせ - 表参道駅周辺",
            "summary": "3/15まで歩道の一部が通行止めになります。通学時は反対側の歩道をご利用ください。",
            "source": "渋谷区役所 土木部",
            "published_at": (now - timedelta(hours=24)).isoformat(),
            "location": "渋谷区神宮前4丁目",
            "lat": 35.6653,
            "lng": 139.7121,
        },
        {
            "id": "news-004",
            "type": "weather",
            "title": "大雨警報発令中 - 東京都全域",
            "summary": "本日夕方から夜にかけて激しい雨の見込み。河川の増水に注意。下校時はお迎えを推奨します。",
            "source": "気象庁",
            "published_at": (now - timedelta(minutes=30)).isoformat(),
            "location": None,
            "lat": 35.6812,
            "lng": 139.7671,
        },
        {
            "id": "news-005",
            "type": "suspicious_person",
            "title": "不審車両の目撃情報 - 世田谷区経堂",
            "summary": "黒いワンボックスカーが小学校周辺を低速で周回している旨の通報がありました。ナンバー一部判明。",
            "source": "警察庁 安全・安心メール",
            "published_at": (now - timedelta(hours=8)).isoformat(),
            "location": "世田谷区経堂2丁目",
            "lat": 35.6500,
            "lng": 139.6350,
        },
        {
            "id": "news-006",
            "type": "event",
            "title": "地域安全パトロール実施のお知らせ",
            "summary": "3/14(土) 15:00-17:00 に地域ボランティアによる通学路パトロールを実施します。参加者募集中。",
            "source": "渋谷区町会連合会",
            "published_at": (now - timedelta(hours=12)).isoformat(),
            "location": "渋谷区全域",
            "lat": 35.6640,
            "lng": 139.6982,
        },
        {
            "id": "news-007",
            "type": "traffic_accident",
            "title": "スクールゾーン内の速度違反取締強化",
            "summary": "新宿区内のスクールゾーンで速度違反の取締りを強化しています。通学時間帯は特にご注意ください。",
            "source": "新宿警察署",
            "published_at": (now - timedelta(hours=18)).isoformat(),
            "location": "新宿区西新宿",
            "lat": 35.6938,
            "lng": 139.6917,
        },
        {
            "id": "news-008",
            "type": "construction",
            "title": "水道管工事による通行規制 - 目黒区",
            "summary": "3/10〜3/20の間、目黒通りの一部区間で車線規制を実施。歩行者通路も変更されます。",
            "source": "東京都水道局",
            "published_at": (now - timedelta(days=2)).isoformat(),
            "location": "目黒区目黒1丁目",
            "lat": 35.6333,
            "lng": 139.7156,
        },
    ]


def _haversine_approx_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """簡易距離計算 (メートル)。日本付近で十分な精度。"""
    dlat = abs(lat1 - lat2) * 111_000
    dlng = abs(lng1 - lng2) * 91_000  # cos(35deg) ≈ 0.82
    return (dlat**2 + dlng**2) ** 0.5


@router.get("/news", response_model=LocalNewsListResponse, summary="地域の安全ニュース")
async def get_local_news(
    lat: float | None = Query(None, ge=-90, le=90, description="緯度"),
    lng: float | None = Query(None, ge=-180, le=180, description="経度"),
    radius: float = Query(5000, ge=100, le=50000, description="検索半径 (メートル)"),
    current_user: User = Depends(get_current_user),
):
    """
    地域の安全に関するニュース・情報を取得する。
    lat/lng が指定された場合、指定地点から radius メートル以内のニュースに絞り込む。
    将来的に警察庁・気象庁・自治体等の外部データソースに接続予定。
    """
    items = _build_sample_news()

    if lat is not None and lng is not None:
        filtered = []
        for item in items:
            dist = _haversine_approx_meters(lat, lng, item["lat"], item["lng"])
            if dist <= radius:
                filtered.append(item)
        items = filtered

    # published_at 降順 (新しいものが先)
    items.sort(key=lambda x: x["published_at"], reverse=True)

    news = [
        LocalNewsItem(
            id=item["id"],
            type=item["type"],
            title=item["title"],
            summary=item["summary"],
            source=item["source"],
            published_at=item["published_at"],
            location=item.get("location"),
        )
        for item in items
    ]

    return LocalNewsListResponse(news=news, total=len(news))


@router.get("/dangers", response_model=DangerZoneListResponse, summary="近隣の危険エリア一覧")
async def list_danger_zones(
    latitude: float = Query(..., ge=-90, le=90, description="中心緯度"),
    longitude: float = Query(..., ge=-180, le=180, description="中心経度"),
    radius: float = Query(3000, ge=100, le=50000, description="検索半径 (メートル)"),
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
    radius_km = radius / 1000.0
    lat_range = radius_km / 111.0
    lng_range = radius_km / 91.0

    query = select(DangerZone).where(
        DangerZone.is_active == True,
        DangerZone.latitude >= latitude - lat_range,
        DangerZone.latitude <= latitude + lat_range,
        DangerZone.longitude >= longitude - lng_range,
        DangerZone.longitude <= longitude + lng_range,
    )

    if risk_type:
        query = query.where(DangerZone.risk_type == risk_type)

    # 有効期限チェック
    query = query.where(
        (DangerZone.expires_at == None) |
        (DangerZone.expires_at > datetime.now(timezone.utc))
    )

    result = await db.execute(query.order_by(DangerZone.risk_level.desc()))
    filtered_zones = list(result.scalars().all())

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
        latitude=data.latitude,
        longitude=data.longitude,
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

    return DangerZoneResponse.model_validate(danger_zone)


@router.post(
    "/dangers/{zone_id}/confirm",
    response_model=DangerZoneResponse,
    summary="危険エリアを確認",
)
async def confirm_danger_zone(
    zone_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    報告された危険エリアを確認（同意）する。
    確認数が増えるほど信頼度が上がる。3件以上で verified フラグが立つ。
    """
    import uuid as _uuid
    result = await db.execute(
        select(DangerZone).where(DangerZone.id == _uuid.UUID(zone_id))
    )
    zone = result.scalar_one_or_none()

    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="危険エリアが見つかりません",
        )

    zone.confirm_count = (zone.confirm_count or 0) + 1
    if zone.confirm_count >= 3:
        zone.verified = True

    await db.flush()
    await db.refresh(zone)

    return DangerZoneResponse.model_validate(zone)


@router.get("/heatmap", response_model=HeatmapResponse, summary="安全ヒートマップデータ")
async def get_safety_heatmap(
    latitude: float = Query(..., ge=-90, le=90, description="中心緯度"),
    longitude: float = Query(..., ge=-180, le=180, description="中心経度"),
    radius: float = Query(3000, ge=100, le=50000, description="半径 (メートル)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    指定エリアの安全ヒートマップデータを返す。
    危険エリアの情報を集約し、ヒートマップ表示用のデータを生成する。
    """
    # バウンディングボックスで危険エリアを取得
    radius_km = radius / 1000.0
    lat_range = radius_km / 111.0
    lng_range = radius_km / 91.0

    result = await db.execute(
        select(DangerZone).where(
            DangerZone.is_active == True,
            DangerZone.latitude >= latitude - lat_range,
            DangerZone.latitude <= latitude + lat_range,
            DangerZone.longitude >= longitude - lng_range,
            DangerZone.longitude <= longitude + lng_range,
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
                latitude=zone.latitude,
                longitude=zone.longitude,
                weight=weight,
                risk_type=zone.risk_type,
            )
        )

    return HeatmapResponse(
        points=points,
        center_latitude=latitude,
        center_longitude=longitude,
        radius_meters=radius,
    )

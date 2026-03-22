"""犯罪データ定期同期パイプライン"""

import csv
import io
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.danger_zone import DangerZone, RiskType, DangerZoneSource

logger = logging.getLogger(__name__)
JST = timezone(timedelta(hours=9))

# 警視庁オープンデータのURL候補
KEISHICHO_DATA_URLS = [
    "https://www.keishicho.metro.tokyo.lg.jp/about_mpd/jokyo_tokei/jokyo/ninchikensu.html",
]

# 犯罪種別マッピング
CRIME_CATEGORIES = {
    "ひったくり": {"risk_type": RiskType.CRIME, "risk_level": 7, "radius": 150},
    "路上強盗": {"risk_type": RiskType.CRIME, "risk_level": 9, "radius": 100},
    "空き巣": {"risk_type": RiskType.CRIME, "risk_level": 5, "radius": 200},
    "自転車盗": {"risk_type": RiskType.CRIME, "risk_level": 3, "radius": 300},
    "車上ねらい": {"risk_type": RiskType.CRIME, "risk_level": 4, "radius": 200},
    "痴漢・わいせつ": {"risk_type": RiskType.CRIME, "risk_level": 8, "radius": 100},
    "声かけ事案": {
        "risk_type": RiskType.SUSPICIOUS_PERSON,
        "risk_level": 6,
        "radius": 150,
    },
    "傷害": {"risk_type": RiskType.CRIME, "risk_level": 8, "radius": 100},
    "交通事故（死亡）": {"risk_type": RiskType.TRAFFIC, "risk_level": 9, "radius": 100},
    "交通事故（重傷）": {"risk_type": RiskType.TRAFFIC, "risk_level": 7, "radius": 150},
    "交通事故（軽傷）": {"risk_type": RiskType.TRAFFIC, "risk_level": 4, "radius": 200},
}

# 不審者情報API（各県警の公開API）
FUSHINSHA_APIS = [
    # 警視庁メール配信データ（形式はCSV/JSON）
    # 実際のAPIが公開されたら追加
]


async def fetch_keishicho_csv() -> list[dict] | None:
    """警視庁オープンデータCSVの取得を試みる"""
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for url in KEISHICHO_DATA_URLS:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    content_type = resp.headers.get("content-type", "")
                    if "csv" in content_type or url.endswith(".csv"):
                        return _parse_csv(resp.text)
            except Exception as e:
                logger.warning(f"データ取得失敗: {url}: {e}")
    return None


def _parse_csv(csv_text: str) -> list[dict]:
    """CSV形式の犯罪データをパースする"""
    records = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        lat = row.get("緯度") or row.get("latitude")
        lng = row.get("経度") or row.get("longitude")
        if lat and lng:
            records.append(
                {
                    "latitude": float(lat),
                    "longitude": float(lng),
                    "title": row.get("種別", row.get("罪名", "犯罪情報")),
                    "description": row.get("概要", ""),
                }
            )
    return records


async def cleanup_expired_zones(session: AsyncSession) -> int:
    """期限切れの危険ゾーンを非アクティブ化する"""
    from sqlalchemy import update

    result = await session.execute(
        update(DangerZone)
        .where(
            DangerZone.expires_at != None,
            DangerZone.expires_at < datetime.now(timezone.utc),
            DangerZone.is_active == True,
        )
        .values(is_active=False)
    )
    count = result.rowcount
    if count:
        logger.info(f"{count}件の期限切れ危険ゾーンを非アクティブ化")
    return count


async def sync_crime_data() -> dict:
    """
    犯罪データの定期同期を実行する。

    1. 期限切れゾーンを非アクティブ化
    2. 警視庁オープンデータの取得を試行
    3. 取得できたデータをDangerZoneに追加（重複チェック付き）

    Returns:
        同期結果の統計情報
    """
    stats = {"expired_cleaned": 0, "new_records": 0, "source": "none"}

    try:
        async with async_session_factory() as session:
            # Step 1: 期限切れクリーンアップ
            stats["expired_cleaned"] = await cleanup_expired_zones(session)

            # Step 2: 新規データ取得
            new_data = await fetch_keishicho_csv()

            if new_data:
                stats["source"] = "keishicho_opendata"
                for record in new_data:
                    # 同一座標（半径50m以内）に既存データがあるかチェック
                    existing = await session.execute(
                        select(func.count())
                        .select_from(DangerZone)
                        .where(
                            DangerZone.latitude.between(
                                record["latitude"] - 0.0005,
                                record["latitude"] + 0.0005,
                            ),
                            DangerZone.longitude.between(
                                record["longitude"] - 0.0005,
                                record["longitude"] + 0.0005,
                            ),
                            DangerZone.is_active == True,
                        )
                    )
                    if (existing.scalar() or 0) > 0:
                        continue  # 重複スキップ

                    zone = DangerZone(
                        latitude=record["latitude"],
                        longitude=record["longitude"],
                        radius_meters=100.0,
                        risk_level=5,
                        risk_type=RiskType.CRIME,
                        title=record["title"][:200],
                        description=record.get("description"),
                        source=DangerZoneSource.POLICE,
                        is_active=True,
                        verified=True,
                        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                    )
                    session.add(zone)
                    stats["new_records"] += 1
            else:
                stats["source"] = "no_data_available"

            await session.commit()

    except Exception as e:
        logger.error(f"犯罪データ同期失敗: {e}")
        stats["error"] = str(e)

    logger.info(f"犯罪データ同期完了: {stats}")
    return stats

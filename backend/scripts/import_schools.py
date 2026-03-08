"""
日本全国の小学校マスターデータをインポートするスクリプト

データソース: 国土数値情報（国土交通省）学校データ P29
https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P29-v2_0.html

使い方:
    cd backend && source .venv/bin/activate && python scripts/import_schools.py
"""

import asyncio
import json
import os
import re
import sys
import uuid
import zipfile
from pathlib import Path

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 国土数値情報 学校データ（令和3年・全国）
DATA_URL = "https://nlftp.mlit.go.jp/ksj/gml/data/P29/P29-21/P29-21_GML.zip"
ZIP_FILENAME = "P29-21_GML.zip"
GEOJSON_FILENAME = "P29-21.geojson"

# 小学校の学校種別コード
ELEMENTARY_SCHOOL_CODE = 16001

# 都道府県コードマッピング
PREFECTURE_MAP = {
    "01": "北海道", "02": "青森県", "03": "岩手県", "04": "宮城県", "05": "秋田県",
    "06": "山形県", "07": "福島県", "08": "茨城県", "09": "栃木県", "10": "群馬県",
    "11": "埼玉県", "12": "千葉県", "13": "東京都", "14": "神奈川県", "15": "新潟県",
    "16": "富山県", "17": "石川県", "18": "福井県", "19": "山梨県", "20": "長野県",
    "21": "岐阜県", "22": "静岡県", "23": "愛知県", "24": "三重県", "25": "滋賀県",
    "26": "京都府", "27": "大阪府", "28": "兵庫県", "29": "奈良県", "30": "和歌山県",
    "31": "鳥取県", "32": "島根県", "33": "岡山県", "34": "広島県", "35": "山口県",
    "36": "徳島県", "37": "香川県", "38": "愛媛県", "39": "高知県", "40": "福岡県",
    "41": "佐賀県", "42": "長崎県", "43": "熊本県", "44": "大分県", "45": "宮崎県",
    "46": "鹿児島県", "47": "沖縄県",
}

# 市区町村抽出パターン
# 「〇〇市」「〇〇区」「〇〇町」「〇〇村」「〇〇郡〇〇町」「〇〇郡〇〇村」を抽出
CITY_PATTERN = re.compile(
    r"^(.+?[市区])"  # 〇〇市 or 〇〇区 (政令市の区含む)
    r"|^(.+?郡.+?[町村])"  # 〇〇郡〇〇町/村
    r"|^(.+?[町村])"  # 〇〇町/村 (郡なし)
)


def extract_city(address: str) -> str | None:
    """住所から市区町村名を抽出する"""
    if not address:
        return None

    # 政令指定都市の場合: 「札幌市南区」→「札幌市」
    m = re.match(r"^(.+?市).+?区", address)
    if m:
        return m.group(1)

    # 東京都特別区: 「千代田区」
    m = re.match(r"^(.+?区)", address)
    if m:
        return m.group(1)

    # 郡部: 「河西郡更別村」
    m = re.match(r"^(.+?郡.+?[町村])", address)
    if m:
        return m.group(1)

    # 市: 「函館市」
    m = re.match(r"^(.+?市)", address)
    if m:
        return m.group(1)

    # 町村: 「〇〇町」「〇〇村」
    m = re.match(r"^(.+?[町村])", address)
    if m:
        return m.group(1)

    return None


def download_data(scripts_dir: Path) -> Path:
    """国土数値情報の学校データをダウンロードする"""
    zip_path = scripts_dir / ZIP_FILENAME
    geojson_path = scripts_dir / GEOJSON_FILENAME

    if geojson_path.exists():
        print(f"  GeoJSONファイルが既に存在します: {geojson_path}")
        return geojson_path

    if not zip_path.exists():
        print(f"  ダウンロード中: {DATA_URL}")
        with httpx.Client(timeout=120.0) as client:
            response = client.get(DATA_URL)
            response.raise_for_status()
            zip_path.write_bytes(response.content)
        print(f"  ダウンロード完了: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        print(f"  ZIPファイルが既に存在します: {zip_path}")

    print(f"  解凍中: {GEOJSON_FILENAME}")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extract(GEOJSON_FILENAME, scripts_dir)

    return geojson_path


def parse_schools(geojson_path: Path) -> list[dict]:
    """GeoJSONファイルから小学校データを抽出する"""
    print(f"  GeoJSONファイル読み込み中: {geojson_path}")
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total = len(data["features"])
    schools = []

    for feature in data["features"]:
        props = feature["properties"]

        # 小学校のみフィルタリング (P29_003 = 16001)
        if props.get("P29_003") != ELEMENTARY_SCHOOL_CODE:
            continue

        coords = feature["geometry"]["coordinates"]
        city_code = props.get("P29_001", "")
        pref_code = city_code[:2] if len(city_code) >= 2 else ""
        prefecture = PREFECTURE_MAP.get(pref_code)
        address = props.get("P29_005", "")
        city = extract_city(address)

        school = {
            "id": uuid.uuid4(),
            "name": props.get("P29_004", ""),
            "address": f"{prefecture}{address}" if prefecture and address else address,
            "longitude": coords[0] if coords else None,
            "latitude": coords[1] if coords else None,
            "prefecture": prefecture,
            "city": city,
        }
        schools.append(school)

    print(f"  全レコード数: {total}, 小学校数: {len(schools)}")
    return schools


async def import_schools(schools: list[dict], database_url: str, batch_size: int = 500):
    """小学校データをデータベースにインポートする"""
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 既存データの確認
        result = await session.execute(text("SELECT count(*) FROM schools"))
        existing_count = result.scalar()
        print(f"  既存レコード数: {existing_count}")

        if existing_count > 0:
            # 既存の学校名+都道府県+市区町村の組み合わせを取得
            result = await session.execute(
                text("SELECT name, prefecture, city FROM schools")
            )
            existing_keys = {(row[0], row[1], row[2]) for row in result.fetchall()}
            print(f"  既存のユニークキー数: {len(existing_keys)}")
        else:
            existing_keys = set()

        # 重複除外
        new_schools = []
        seen_keys = set()
        skipped_dup = 0
        for s in schools:
            key = (s["name"], s["prefecture"], s["city"])
            if key in existing_keys or key in seen_keys:
                skipped_dup += 1
                continue
            seen_keys.add(key)
            new_schools.append(s)

        print(f"  新規インポート対象: {len(new_schools)} 件 (重複スキップ: {skipped_dup} 件)")

        if not new_schools:
            print("  インポートするデータがありません。")
            await engine.dispose()
            return

        # バッチインサート
        total = len(new_schools)
        for i in range(0, total, batch_size):
            batch = new_schools[i : i + batch_size]
            values_list = []
            params = {}
            for j, school in enumerate(batch):
                idx = i + j
                values_list.append(
                    f"(:id_{idx}, :name_{idx}, :address_{idx}, :latitude_{idx}, "
                    f":longitude_{idx}, :prefecture_{idx}, :city_{idx}, now())"
                )
                params[f"id_{idx}"] = str(school["id"])
                params[f"name_{idx}"] = school["name"]
                params[f"address_{idx}"] = school["address"]
                params[f"latitude_{idx}"] = school["latitude"]
                params[f"longitude_{idx}"] = school["longitude"]
                params[f"prefecture_{idx}"] = school["prefecture"]
                params[f"city_{idx}"] = school["city"]

            sql = (
                "INSERT INTO schools (id, name, address, latitude, longitude, prefecture, city, created_at) "
                f"VALUES {', '.join(values_list)}"
            )
            await session.execute(text(sql), params)
            progress = min(i + batch_size, total)
            print(f"  進捗: {progress}/{total} ({progress * 100 // total}%)")

        await session.commit()
        print(f"  コミット完了！ {len(new_schools)} 件をインポートしました。")

    await engine.dispose()


async def main():
    print("=" * 60)
    print("日本全国 小学校マスターデータ インポート")
    print("データソース: 国土数値情報（国土交通省）学校データ P29")
    print("=" * 60)

    # データベースURL
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://guardian:guardian@localhost:5434/guardian_ai",
    )
    print(f"\nDB: {database_url}")

    scripts_dir = Path(__file__).resolve().parent

    # Step 1: データダウンロード
    print("\n[1/3] データダウンロード")
    geojson_path = download_data(scripts_dir)

    # Step 2: データパース
    print("\n[2/3] データパース（小学校フィルタリング）")
    schools = parse_schools(geojson_path)

    # Step 3: DBインポート
    print("\n[3/3] データベースインポート")
    await import_schools(schools, database_url)

    print("\n完了！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

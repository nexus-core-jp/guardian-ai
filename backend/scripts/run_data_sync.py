#!/usr/bin/env python3
"""
データ同期バッチランナー

全てのデータ取得スクリプトを順番に実行する。
cron や systemd timer から呼び出して定期実行する想定。

Usage:
    cd backend && source .venv/bin/activate && python scripts/run_data_sync.py

cron 設定例（毎日午前6時に実行）:
    0 6 * * * cd /path/to/backend && .venv/bin/python scripts/run_data_sync.py >> /var/log/guardian-sync.log 2>&1

オプション:
    --force    既存データがあっても上書き更新する
"""

import asyncio
import logging
import subprocess
import sys
import os
import time
from datetime import datetime, timezone, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)

# 実行するスクリプトの一覧（順番に実行）
DATA_FETCHERS = [
    {
        "name": "犯罪統計データ取得",
        "script": "fetch_crime_data.py",
        "description": "警察庁・警視庁オープンデータから犯罪発生情報を取得",
    },
    {
        "name": "不審者情報取得",
        "script": "fetch_fushinsha.py",
        "description": "都道府県の不審者情報を取得",
    },
]


def run_fetcher(fetcher: dict, extra_args: list[str]) -> bool:
    """個別のフェッチャースクリプトを実行する"""
    script_path = os.path.join(SCRIPTS_DIR, fetcher["script"])

    if not os.path.exists(script_path):
        logger.error(f"スクリプトが見つかりません: {script_path}")
        return False

    logger.info(f"--- {fetcher['name']} 開始 ---")
    logger.info(f"  {fetcher['description']}")

    cmd = [sys.executable, script_path] + extra_args
    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True,
            timeout=300,  # 5分タイムアウト
        )

        elapsed = time.time() - start_time

        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                logger.info(f"  [stdout] {line}")

        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                if "ERROR" in line or "error" in line:
                    logger.error(f"  [stderr] {line}")
                else:
                    logger.info(f"  [stderr] {line}")

        if result.returncode == 0:
            logger.info(f"--- {fetcher['name']} 完了 ({elapsed:.1f}秒) ---")
            return True
        else:
            logger.error(f"--- {fetcher['name']} 失敗 (return code: {result.returncode}, {elapsed:.1f}秒) ---")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"--- {fetcher['name']} タイムアウト ---")
        return False
    except Exception as e:
        logger.error(f"--- {fetcher['name']} エラー: {e} ---")
        return False


def main() -> None:
    """メイン処理"""
    now = datetime.now(JST)
    logger.info("=" * 60)
    logger.info(f"Guardian AI データ同期バッチ 開始: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info("=" * 60)

    extra_args = []
    if "--force" in sys.argv:
        extra_args.append("--force")
        logger.info("強制更新モード (--force)")

    total = len(DATA_FETCHERS)
    success = 0
    failed = 0

    for i, fetcher in enumerate(DATA_FETCHERS, 1):
        logger.info(f"\n[{i}/{total}] {fetcher['name']}")
        if run_fetcher(fetcher, extra_args):
            success += 1
        else:
            failed += 1

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Guardian AI データ同期バッチ 完了")
    logger.info(f"  成功: {success}/{total}  失敗: {failed}/{total}")
    logger.info("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

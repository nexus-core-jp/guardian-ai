"""バックグラウンドタスクスケジューラー"""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.database import async_session_factory
from app.services.alert_service import AlertService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def escalation_check_job() -> None:
    """
    未解決アラートのエスカレーションチェック（定期実行）
    - info → warning: 30分経過
    - warning → critical: 10分経過
    - critical → emergency: 5分経過
    """
    logger.debug("エスカレーションチェック開始")
    try:
        async with async_session_factory() as session:
            alert_service = AlertService(session)
            escalated = await alert_service.check_and_escalate()
            if escalated:
                # エスカレーションされたアラートをWebSocket経由でもブロードキャスト
                from app.services.websocket_manager import ws_manager
                for alert in escalated:
                    await ws_manager.broadcast_alert(
                        child_id=str(alert.child_id),
                        alert_data={
                            "id": str(alert.id),
                            "alert_type": alert.alert_type,
                            "severity": alert.severity,
                            "title": alert.title,
                            "message": alert.message or "",
                            "child_id": str(alert.child_id),
                        },
                    )
                logger.info(f"{len(escalated)}件のアラートをエスカレーション")
            await session.commit()
    except Exception as e:
        logger.error(f"エスカレーションチェック失敗: {e}")


async def stale_location_check_job() -> None:
    """
    位置情報の鮮度チェック（定期実行）
    一定時間更新がない子どもの端末について device_offline アラートを生成する。
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select, func
    from app.models.child import Child
    from app.models.location import Location
    from app.models.alert import AlertType, AlertSeverity

    logger.debug("位置情報鮮度チェック開始")
    try:
        async with async_session_factory() as session:
            # 30分以上更新がないアクティブな子どもを検出
            threshold = datetime.now(timezone.utc) - timedelta(minutes=30)

            # 子ども毎の最新位置情報タイムスタンプを取得
            subquery = (
                select(
                    Location.child_id,
                    func.max(Location.timestamp).label("latest_ts"),
                )
                .group_by(Location.child_id)
                .subquery()
            )

            result = await session.execute(
                select(Child, subquery.c.latest_ts)
                .outerjoin(subquery, Child.id == subquery.c.child_id)
                .where(
                    Child.is_active == True,
                    (subquery.c.latest_ts < threshold) | (subquery.c.latest_ts == None),
                )
            )
            stale_children = result.all()

            if not stale_children:
                return

            alert_service = AlertService(session)
            for child, latest_ts in stale_children:
                if latest_ts is None:
                    # まだ位置情報が一度も記録されていない場合はスキップ
                    continue

                minutes_ago = int(
                    (datetime.now(timezone.utc) - latest_ts.replace(tzinfo=timezone.utc)).total_seconds() / 60
                )

                await alert_service.create_alert(
                    child_id=child.id,
                    user_id=child.user_id,
                    alert_type=AlertType.DEVICE_OFFLINE,
                    severity=AlertSeverity.WARNING,
                    title="デバイスオフライン",
                    message=f"{child.name}のGPSデバイスから{minutes_ago}分間更新がありません",
                )

            await session.commit()
            if stale_children:
                logger.info(f"{len(stale_children)}件のデバイスオフラインアラート")

    except Exception as e:
        logger.error(f"位置情報鮮度チェック失敗: {e}")


async def crime_data_sync_job() -> None:
    """犯罪データの定期同期（毎日AM3:00 JST）"""
    logger.info("犯罪データ定期同期開始")
    try:
        from app.services.crime_data_sync import sync_crime_data
        stats = await sync_crime_data()
        logger.info(f"犯罪データ同期結果: {stats}")
    except Exception as e:
        logger.error(f"犯罪データ同期失敗: {e}")


def start_scheduler() -> None:
    """スケジューラーを起動する"""
    # エスカレーションチェック: 1分間隔
    scheduler.add_job(
        escalation_check_job,
        trigger=IntervalTrigger(minutes=1),
        id="escalation_check",
        name="アラートエスカレーションチェック",
        replace_existing=True,
    )

    # デバイスオフラインチェック: 5分間隔
    scheduler.add_job(
        stale_location_check_job,
        trigger=IntervalTrigger(minutes=5),
        id="stale_location_check",
        name="位置情報鮮度チェック",
        replace_existing=True,
    )

    # 犯罪データ定期同期: 毎日AM3:00(JST)に実行
    scheduler.add_job(
        crime_data_sync_job,
        trigger=CronTrigger(hour=18, minute=0),  # UTC 18:00 = JST 03:00
        id="crime_data_sync",
        name="犯罪データ定期同期",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("バックグラウンドスケジューラー起動完了")


def stop_scheduler() -> None:
    """スケジューラーを停止する"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("バックグラウンドスケジューラー停止")

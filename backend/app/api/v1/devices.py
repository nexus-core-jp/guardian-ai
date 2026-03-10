"""GPSデバイスWebhookエンドポイント"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.gps_device import get_adapter, process_device_locations

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/webhook/{device_type}",
    status_code=status.HTTP_200_OK,
    summary="GPSデバイスWebhook受信",
)
async def device_webhook(
    device_type: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    GPSデバイスからのWebhookを受信する。

    対応デバイス:
    - bot: BoT (Bsize) GPSトラッカー
    - mitsune: みつね GPSトラッカー
    - generic: 汎用フォーマット

    使用例: POST /api/v1/devices/webhook/bot
    """
    adapter = get_adapter(device_type)

    # リクエストボディを取得
    body = await request.body()
    payload = await request.json()

    # 署名検証（X-Signature ヘッダー）
    signature = request.headers.get("X-Signature", "")
    if not adapter.verify_signature(body, signature):
        logger.warning(f"Webhook署名検証失敗: device_type={device_type}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="署名検証に失敗しました",
        )

    # ペイロードをパース
    try:
        device_locations = adapter.parse_webhook(payload, dict(request.headers))
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Webhookペイロードパース失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ペイロードの形式が不正です: {e}",
        )

    if not device_locations:
        return {"status": "ok", "processed": 0}

    # 位置情報を処理（保存 + 異常検知 + WS配信）
    saved = await process_device_locations(db, device_locations)

    logger.info(
        f"Webhook処理完了: device_type={device_type}, "
        f"received={len(device_locations)}, saved={len(saved)}"
    )

    return {"status": "ok", "processed": len(saved)}

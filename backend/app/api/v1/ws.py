"""WebSocketエンドポイント — リアルタイム位置情報配信"""

import uuid
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt

from app.config import get_settings
from app.services.websocket_manager import ws_manager

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter()


def _authenticate_token(token: str) -> uuid.UUID | None:
    """JWTトークンからuser_idを取得する"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = payload.get("sub")
        if user_id:
            return uuid.UUID(user_id)
    except (JWTError, ValueError):
        pass
    return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    リアルタイム位置情報WebSocket

    接続: ws://host/api/v1/ws?token=<JWT>

    クライアント→サーバー メッセージ:
        {"action": "subscribe", "child_id": "<uuid>"}
        {"action": "unsubscribe", "child_id": "<uuid>"}
        {"action": "ping"}

    サーバー→クライアント メッセージ:
        {"type": "location_update", "child_id": "<uuid>", "data": {...}}
        {"type": "alert", "data": {...}}
        {"type": "pong"}
        {"type": "error", "message": "..."}
    """
    # JWT認証
    user_id = _authenticate_token(token)
    if user_id is None:
        await websocket.close(code=4001, reason="認証失敗")
        return

    await ws_manager.connect(websocket, user_id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "無効なJSONです"})
                )
                continue

            action = msg.get("action")

            if action == "subscribe":
                child_id_str = msg.get("child_id")
                if child_id_str:
                    try:
                        child_id = uuid.UUID(child_id_str)
                        ws_manager.subscribe(user_id, child_id)
                        await websocket.send_text(
                            json.dumps(
                                {"type": "subscribed", "child_id": str(child_id)}
                            )
                        )
                    except ValueError:
                        await websocket.send_text(
                            json.dumps(
                                {"type": "error", "message": "無効なchild_idです"}
                            )
                        )

            elif action == "unsubscribe":
                child_id_str = msg.get("child_id")
                if child_id_str:
                    try:
                        child_id = uuid.UUID(child_id_str)
                        ws_manager.unsubscribe(user_id, child_id)
                        await websocket.send_text(
                            json.dumps(
                                {"type": "unsubscribed", "child_id": str(child_id)}
                            )
                        )
                    except ValueError:
                        pass

            elif action == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            else:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": f"不明なaction: {action}"})
                )

    except WebSocketDisconnect:
        ws_manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocketエラー: {e}")
        ws_manager.disconnect(user_id)

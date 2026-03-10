"""WebSocket接続マネージャー — リアルタイム位置情報配信"""

import json
import logging
import uuid
from dataclasses import dataclass, field

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """WebSocket接続情報"""
    websocket: WebSocket
    user_id: uuid.UUID
    child_ids: set[uuid.UUID] = field(default_factory=set)


class WebSocketManager:
    """
    WebSocket接続を管理し、子どもの位置情報更新をリアルタイムで配信する。

    接続フロー:
    1. 保護者がWebSocketに接続（JWT認証）
    2. 監視対象の子どもIDを購読
    3. 位置情報が記録されるたびにブロードキャスト
    """

    def __init__(self):
        # user_id -> ConnectionInfo
        self._connections: dict[uuid.UUID, ConnectionInfo] = {}
        # child_id -> set of user_ids（逆引きインデックス）
        self._child_subscribers: dict[uuid.UUID, set[uuid.UUID]] = {}

    async def connect(self, websocket: WebSocket, user_id: uuid.UUID) -> None:
        """新しいWebSocket接続を受け入れる"""
        await websocket.accept()
        self._connections[user_id] = ConnectionInfo(
            websocket=websocket,
            user_id=user_id,
        )
        logger.info(f"WebSocket接続: user_id={user_id}")

    def disconnect(self, user_id: uuid.UUID) -> None:
        """WebSocket接続を切断する"""
        conn = self._connections.pop(user_id, None)
        if conn:
            # 購読解除
            for child_id in conn.child_ids:
                subs = self._child_subscribers.get(child_id)
                if subs:
                    subs.discard(user_id)
                    if not subs:
                        del self._child_subscribers[child_id]
        logger.info(f"WebSocket切断: user_id={user_id}")

    def subscribe(self, user_id: uuid.UUID, child_id: uuid.UUID) -> None:
        """子どもの位置情報更新を購読する"""
        conn = self._connections.get(user_id)
        if conn is None:
            return
        conn.child_ids.add(child_id)
        self._child_subscribers.setdefault(child_id, set()).add(user_id)
        logger.debug(f"購読開始: user_id={user_id}, child_id={child_id}")

    def unsubscribe(self, user_id: uuid.UUID, child_id: uuid.UUID) -> None:
        """購読を解除する"""
        conn = self._connections.get(user_id)
        if conn:
            conn.child_ids.discard(child_id)
        subs = self._child_subscribers.get(child_id)
        if subs:
            subs.discard(user_id)

    async def broadcast_location(
        self,
        child_id: uuid.UUID,
        location_data: dict,
    ) -> None:
        """
        子どもの位置情報更新を購読者全員にブロードキャストする。

        Args:
            child_id: 子どものID
            location_data: 位置情報データ（LocationResponse相当）
        """
        subscriber_ids = self._child_subscribers.get(child_id, set())
        if not subscriber_ids:
            return

        message = json.dumps({
            "type": "location_update",
            "child_id": str(child_id),
            "data": location_data,
        }, ensure_ascii=False)

        disconnected = []
        for user_id in subscriber_ids:
            conn = self._connections.get(user_id)
            if conn is None:
                disconnected.append(user_id)
                continue
            try:
                await conn.websocket.send_text(message)
            except Exception:
                disconnected.append(user_id)
                logger.warning(f"WebSocket送信失敗: user_id={user_id}")

        # 切断された接続をクリーンアップ
        for user_id in disconnected:
            self.disconnect(user_id)

    async def broadcast_alert(
        self,
        user_id: uuid.UUID,
        alert_data: dict,
    ) -> None:
        """アラートをリアルタイムで保護者に送信する"""
        conn = self._connections.get(user_id)
        if conn is None:
            return

        message = json.dumps({
            "type": "alert",
            "data": alert_data,
        }, ensure_ascii=False)

        try:
            await conn.websocket.send_text(message)
        except Exception:
            self.disconnect(user_id)

    @property
    def active_connections(self) -> int:
        return len(self._connections)


# シングルトンインスタンス
ws_manager = WebSocketManager()

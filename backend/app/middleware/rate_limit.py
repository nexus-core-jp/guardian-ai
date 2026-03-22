"""レートリミティングミドルウェア（Redis対応）"""

import time
import logging
from dataclasses import dataclass

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Redis接続（利用可能な場合）
_redis_client = None

try:
    import redis.asyncio as aioredis
    from app.config import get_settings

    _settings = get_settings()
    if _settings.REDIS_URL:
        _redis_client = aioredis.from_url(
            _settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        logger.info("Redisベースレートリミッター初期化")
except Exception as e:
    logger.info(f"Redisレートリミッターをスキップ、インメモリを使用: {e}")


@dataclass
class RateBucket:
    """トークンバケット"""

    tokens: float
    last_refill: float
    max_tokens: float
    refill_rate: float  # tokens/sec

    def consume(self) -> bool:
        """トークンを消費する。成功すればTrue"""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    @property
    def retry_after(self) -> float:
        """次のトークンが利用可能になるまでの秒数"""
        if self.tokens >= 1.0:
            return 0.0
        return (1.0 - self.tokens) / self.refill_rate


# エンドポイントグループ別のレート設定
RATE_LIMITS = {
    # (max_tokens, refill_rate per second)
    "default": (60, 1.0),  # 60 req/min
    "auth": (10, 0.17),  # 10 req/min
    "locations": (120, 2.0),  # 120 req/min（高頻度GPS送信対応）
    "webhook": (200, 3.33),  # 200 req/min（デバイスWebhook）
    "routes": (30, 0.5),  # 30 req/min
}


def _get_rate_group(path: str) -> str:
    """パスからレートリミットグループを判定する"""
    if "/auth/" in path:
        return "auth"
    if "/locations" in path:
        return "locations"
    if "/devices/webhook" in path:
        return "webhook"
    if "/routes" in path:
        return "routes"
    return "default"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    IPベースのレートリミティングミドルウェア。
    Redis利用可能時は分散レートリミッター、なければインメモリフォールバック。
    """

    def __init__(self, app):
        super().__init__(app)
        self._buckets: dict[tuple[str, str], RateBucket] = {}
        self._cleanup_counter = 0

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_bucket(self, client_ip: str, rate_group: str) -> RateBucket:
        key = (client_ip, rate_group)
        if key not in self._buckets:
            max_tokens, refill_rate = RATE_LIMITS.get(
                rate_group, RATE_LIMITS["default"]
            )
            self._buckets[key] = RateBucket(
                tokens=max_tokens,
                last_refill=time.monotonic(),
                max_tokens=max_tokens,
                refill_rate=refill_rate,
            )
        return self._buckets[key]

    def _cleanup_stale_buckets(self):
        self._cleanup_counter += 1
        if self._cleanup_counter < 1000:
            return
        self._cleanup_counter = 0
        now = time.monotonic()
        stale_keys = [k for k, b in self._buckets.items() if now - b.last_refill > 600]
        for k in stale_keys:
            del self._buckets[k]

    async def _check_redis_rate_limit(
        self, client_ip: str, rate_group: str
    ) -> tuple[bool, float]:
        """Redisベースのスライディングウィンドウレートリミット"""
        max_tokens, _ = RATE_LIMITS.get(rate_group, RATE_LIMITS["default"])
        key = f"ratelimit:{rate_group}:{client_ip}"
        window_seconds = 60

        try:
            pipe = _redis_client.pipeline()
            now = time.time()
            window_start = now - window_seconds

            # 古いエントリを削除して現在のカウントを取得
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, window_seconds + 1)
            results = await pipe.execute()

            current_count = results[1]
            if current_count >= max_tokens:
                return False, window_seconds / max_tokens
            return True, 0.0
        except Exception as e:
            logger.warning(
                f"Redis レートリミットエラー、インメモリにフォールバック: {e}"
            )
            return True, 0.0

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path == "/health" or path.endswith("/ws"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        rate_group = _get_rate_group(path)

        # Redis利用可能ならRedisベース、なければインメモリ
        if _redis_client:
            allowed, retry_after = await self._check_redis_rate_limit(
                client_ip, rate_group
            )
        else:
            bucket = self._get_bucket(client_ip, rate_group)
            allowed = bucket.consume()
            retry_after = bucket.retry_after if not allowed else 0.0

        if not allowed:
            logger.warning(
                f"レートリミット超過: ip={client_ip}, group={rate_group}, "
                f"retry_after={retry_after:.1f}s"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "リクエスト回数が上限を超えました。しばらくしてから再試行してください。",
                },
                headers={"Retry-After": str(int(retry_after) + 1)},
            )

        if not _redis_client:
            self._cleanup_stale_buckets()
        return await call_next(request)

"""Guardian AI - 子どもの安全を見守るAIプラットフォーム"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, close_db
from app.api.v1.router import v1_router
from app.services.scheduler import start_scheduler, stop_scheduler
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security import SecurityHeadersMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    # 起動時
    await init_db()
    start_scheduler()
    yield
    # 終了時
    stop_scheduler()
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="子どもの安全を見守るAIプラットフォーム",
    lifespan=lifespan,
    # 本番環境ではSwagger UIを無効化
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# セキュリティヘッダー
app.add_middleware(SecurityHeadersMiddleware)

# レートリミティング
app.add_middleware(RateLimitMiddleware)

# v1ルーターをマウント
app.include_router(v1_router, prefix="/api/v1")


@app.get("/health", tags=["ヘルスチェック"])
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }

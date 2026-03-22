"""アプリケーション設定"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """環境変数からアプリケーション設定を読み込む"""

    # アプリケーション
    APP_NAME: str = "Guardian AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # データベース
    DATABASE_URL: str = (
        "postgresql+asyncpg://guardian:guardian@localhost:5434/guardian_ai"
    )
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6380/0"

    # LINE Login
    LINE_CHANNEL_ID: str = ""
    LINE_CHANNEL_SECRET: str = ""
    LINE_REDIRECT_URI: str = "http://localhost:8002/api/v1/auth/line/callback"

    # Firebase Cloud Messaging
    FCM_CREDENTIALS_PATH: str = ""

    # 地図API
    MAPBOX_TOKEN: str = ""
    GOOGLE_MAPS_API_KEY: str = ""

    # Apple Sign-In
    APPLE_TEAM_ID: str = ""
    APPLE_BUNDLE_ID: str = "com.guardianai.app"

    # Google Sign-In
    GOOGLE_CLIENT_ID: str = ""

    # GPSデバイス連携
    BOT_WEBHOOK_SECRET: str = ""
    MITSUNE_API_KEY: str = ""

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7日間

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3004",
        "http://localhost:8081",
    ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()

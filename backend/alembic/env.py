"""Alembic マイグレーション環境設定"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Alembic Config
config = context.config

# ロギング設定
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# モデルのメタデータをインポート（自動マイグレーション生成に必要）
from app.database import Base
from app.models import *  # noqa: F401, F403
from app.config import get_settings

target_metadata = Base.metadata

# アプリケーション設定からDB URLを取得してAlembic設定を上書き
_settings = get_settings()
config.set_main_option("sqlalchemy.url", _settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """オフラインモードでマイグレーションを実行する"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """PostGISの内蔵テーブル・スキーマを除外する"""
    if type_ == "table" and name in (
        "spatial_ref_sys", "geometry_columns", "geography_columns",
        "raster_columns", "raster_overviews", "layer", "topology",
    ):
        return False
    # tiger/topology スキーマのテーブルを除外
    if type_ == "table" and reflected and compare_to is None:
        return False
    return True


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """非同期マイグレーションを実行する"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """オンラインモードでマイグレーションを実行する"""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

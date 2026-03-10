"""add PostGIS geometry columns and spatial indexes

Revision ID: c3f2a9e1d456
Revises: a80f468db64e
Create Date: 2026-03-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c3f2a9e1d456'
down_revision: Union[str, None] = 'a80f468db64e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostGIS拡張を有効化
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # --- locations テーブル ---
    op.execute(
        "ALTER TABLE locations ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326)"
    )
    # 既存データのgeom列を生成
    op.execute(
        "UPDATE locations SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) "
        "WHERE geom IS NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_locations_geom ON locations USING GIST (geom)"
    )

    # --- danger_zones テーブル ---
    op.execute(
        "ALTER TABLE danger_zones ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326)"
    )
    op.execute(
        "UPDATE danger_zones SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) "
        "WHERE geom IS NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_danger_zones_geom ON danger_zones USING GIST (geom)"
    )

    # --- geom列の自動更新トリガー: locations ---
    op.execute("""
        CREATE OR REPLACE FUNCTION update_location_geom()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.geom := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_update_location_geom ON locations;
        CREATE TRIGGER trg_update_location_geom
        BEFORE INSERT OR UPDATE OF latitude, longitude ON locations
        FOR EACH ROW EXECUTE FUNCTION update_location_geom();
    """)

    # --- geom列の自動更新トリガー: danger_zones ---
    op.execute("""
        CREATE OR REPLACE FUNCTION update_danger_zone_geom()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.geom := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_update_danger_zone_geom ON danger_zones;
        CREATE TRIGGER trg_update_danger_zone_geom
        BEFORE INSERT OR UPDATE OF latitude, longitude ON danger_zones
        FOR EACH ROW EXECUTE FUNCTION update_danger_zone_geom();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_update_danger_zone_geom ON danger_zones")
    op.execute("DROP FUNCTION IF EXISTS update_danger_zone_geom()")
    op.execute("DROP TRIGGER IF EXISTS trg_update_location_geom ON locations")
    op.execute("DROP FUNCTION IF EXISTS update_location_geom()")
    op.execute("DROP INDEX IF EXISTS ix_danger_zones_geom")
    op.execute("ALTER TABLE danger_zones DROP COLUMN IF EXISTS geom")
    op.execute("DROP INDEX IF EXISTS ix_locations_geom")
    op.execute("ALTER TABLE locations DROP COLUMN IF EXISTS geom")

"""add notification_preferences table and confirm_count to danger_zones

Revision ID: e5f6a7b890c1
Revises: d4e5f6a7b890
Create Date: 2026-03-10 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "e5f6a7b890c1"
down_revision = "d4e5f6a7b890"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # notification_preferences テーブル作成
    op.create_table(
        "notification_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), unique=True, index=True, nullable=False),
        sa.Column("route_deviation", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("danger_zone", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("arrival", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("departure", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("community_reports", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # danger_zones に confirm_count を追加
    op.add_column(
        "danger_zones",
        sa.Column("confirm_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("danger_zones", "confirm_count")
    op.drop_table("notification_preferences")

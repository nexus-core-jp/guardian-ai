"""add apple_id and google_id to users

Revision ID: d4e5f6a7b890
Revises: c3f2a9e1d456
Create Date: 2026-03-10 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b890"
down_revision = "c3f2a9e1d456"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("apple_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("google_id", sa.String(255), nullable=True))
    op.create_index("ix_users_apple_id", "users", ["apple_id"], unique=True)
    op.create_index("ix_users_google_id", "users", ["google_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_google_id", table_name="users")
    op.drop_index("ix_users_apple_id", table_name="users")
    op.drop_column("users", "google_id")
    op.drop_column("users", "apple_id")

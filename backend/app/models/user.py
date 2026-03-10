"""保護者/ガーディアン ユーザーモデル"""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """保護者ユーザー"""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    line_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    apple_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    google_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    email: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fcm_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    home_latitude: Mapped[float | None] = mapped_column(nullable=True)
    home_longitude: Mapped[float | None] = mapped_column(nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # リレーション
    children: Mapped[list["Child"]] = relationship(
        "Child", back_populates="parent", lazy="select"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="user", lazy="select"
    )

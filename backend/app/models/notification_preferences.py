"""通知設定モデル"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NotificationPreferences(Base):
    """ユーザーごとの通知設定"""

    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, index=True
    )
    route_deviation: Mapped[bool] = mapped_column(default=True)
    danger_zone: Mapped[bool] = mapped_column(default=True)
    arrival: Mapped[bool] = mapped_column(default=True)
    departure: Mapped[bool] = mapped_column(default=True)
    community_reports: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

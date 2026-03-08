"""安全ルートモデル"""

import uuid
from datetime import datetime

from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, func, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Route(Base):
    """安全ルート"""

    __tablename__ = "routes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("children.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), default="通学路")
    origin_lat: Mapped[float] = mapped_column(
        Float, nullable=False, comment="出発地点の緯度"
    )
    origin_lng: Mapped[float] = mapped_column(
        Float, nullable=False, comment="出発地点の経度"
    )
    destination_lat: Mapped[float] = mapped_column(
        Float, nullable=False, comment="目的地点の緯度"
    )
    destination_lng: Mapped[float] = mapped_column(
        Float, nullable=False, comment="目的地点の経度"
    )
    waypoints_json: Mapped[list | None] = mapped_column(
        JSON, nullable=True, comment="経由ポイント [{lat, lng, order, safety_score}]"
    )
    distance_meters: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="距離 (メートル)"
    )
    estimated_duration_minutes: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="予想所要時間 (分)"
    )
    safety_score: Mapped[float] = mapped_column(
        Float, default=5.0, comment="安全スコア (1-10)"
    )
    is_recommended: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="推奨ルートかどうか"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # リレーション
    child: Mapped["Child"] = relationship("Child", back_populates="routes")

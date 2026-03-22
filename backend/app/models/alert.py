"""アラート/通知モデル"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, Text, Boolean, DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AlertType(str, PyEnum):
    """アラート種別"""

    ROUTE_DEVIATION = "route_deviation"  # ルート逸脱
    SPEED_ANOMALY = "speed_anomaly"  # 速度異常
    ZONE_ENTRY = "zone_entry"  # 危険エリア侵入
    SOS = "sos"  # SOS
    BATTERY_LOW = "battery_low"  # バッテリー低下
    DEVICE_OFFLINE = "device_offline"  # デバイスオフライン
    GEOFENCE_EXIT = "geofence_exit"  # ジオフェンス外出
    ARRIVAL = "arrival"  # 到着通知
    DEPARTURE = "departure"  # 出発通知


class AlertSeverity(str, PyEnum):
    """アラート重要度"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class Alert(Base):
    """アラート"""

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("children.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    alert_type: Mapped[str] = mapped_column(
        Enum(AlertType, name="alert_type"),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        Enum(AlertSeverity, name="alert_severity"),
        default=AlertSeverity.INFO,
    )
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # リレーション
    child: Mapped["Child"] = relationship("Child", back_populates="alerts")
    user: Mapped["User"] = relationship("User", back_populates="alerts")

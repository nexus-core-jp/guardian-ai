"""位置情報/GPSデータモデル"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Float, DateTime, ForeignKey, Enum, func, Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry

from app.database import Base


class LocationSource(str, PyEnum):
    """位置情報の取得元"""

    GPS_DEVICE = "gps_device"
    APP = "app"
    MANUAL = "manual"


class Location(Base):
    """子どもの位置情報"""

    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("children.id", ondelete="CASCADE"), index=True
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    altitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="移動速度 (m/s)"
    )
    accuracy: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="精度 (メートル)"
    )
    heading: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="方位角 (度)"
    )
    source: Mapped[str] = mapped_column(
        Enum(LocationSource, name="location_source"),
        default=LocationSource.GPS_DEVICE,
    )
    battery_level: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="デバイスバッテリー残量 (%)"
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # PostGIS Geometry列（トリガーでlat/lngから自動生成）
    geom = Column(Geometry("POINT", srid=4326), nullable=True)

    # リレーション
    child: Mapped["Child"] = relationship("Child", back_populates="locations")

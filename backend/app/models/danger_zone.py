"""危険エリアモデル"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    String,
    Integer,
    Float,
    Text,
    DateTime,
    Enum,
    ForeignKey,
    func,
    Column,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry

from app.database import Base


class RiskType(str, PyEnum):
    """リスク種別"""

    SUSPICIOUS_PERSON = "suspicious_person"  # 不審者
    TRAFFIC = "traffic"  # 交通危険
    CRIME = "crime"  # 犯罪
    DARK_AREA = "dark_area"  # 暗い場所
    CONSTRUCTION = "construction"  # 工事中
    NATURAL_HAZARD = "natural_hazard"  # 自然災害リスク
    OTHER = "other"  # その他


class DangerZoneSource(str, PyEnum):
    """情報源"""

    POLICE = "police"  # 警察情報
    COMMUNITY = "community"  # 地域住民からの報告
    AI_ANALYSIS = "ai_analysis"  # AI分析
    GOVERNMENT = "government"  # 行政情報
    SCHOOL = "school"  # 学校からの情報


class DangerZone(Base):
    """危険エリア"""

    __tablename__ = "danger_zones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    latitude: Mapped[float] = mapped_column(
        Float, nullable=False, comment="危険地点の緯度"
    )
    longitude: Mapped[float] = mapped_column(
        Float, nullable=False, comment="危険地点の経度"
    )
    radius_meters: Mapped[float | None] = mapped_column(
        nullable=True, comment="影響半径 (メートル)"
    )
    risk_level: Mapped[int] = mapped_column(
        Integer, default=5, comment="リスクレベル (1-10)"
    )
    risk_type: Mapped[str] = mapped_column(
        Enum(RiskType, name="risk_type"),
        default=RiskType.OTHER,
    )
    title: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(
        Enum(DangerZoneSource, name="danger_zone_source"),
        default=DangerZoneSource.COMMUNITY,
    )
    reported_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="有効期限"
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    verified: Mapped[bool] = mapped_column(default=False, comment="確認済みかどうか")
    confirm_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), comment="確認数"
    )
    # PostGIS Geometry列（トリガーでlat/lngから自動生成）
    geom = Column(Geometry("POINT", srid=4326), nullable=True)

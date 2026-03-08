"""子どもプロフィールモデル"""

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class School(Base):
    """学校マスターデータ"""

    __tablename__ = "schools"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), index=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )
    prefecture: Mapped[str | None] = mapped_column(String(50), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # リレーション
    children: Mapped[list["Child"]] = relationship(
        "Child", back_populates="school", lazy="selectin"
    )


class Child(Base):
    """子どもプロフィール"""

    __tablename__ = "children"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    school_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100))
    grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    device_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, comment="GPSデバイスID"
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # リレーション
    parent: Mapped["User"] = relationship("User", back_populates="children")
    school: Mapped["School | None"] = relationship("School", back_populates="children")
    locations: Mapped[list["Location"]] = relationship(
        "Location", back_populates="child", lazy="selectin"
    )
    routes: Mapped[list["Route"]] = relationship(
        "Route", back_populates="child", lazy="selectin"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="child", lazy="selectin"
    )

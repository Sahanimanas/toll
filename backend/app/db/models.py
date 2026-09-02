from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# JSON that becomes JSONB on PostgreSQL but still works on SQLite (tests).
JsonCol = JSON().with_variant(JSONB(), "postgresql")
# BigInteger PK that autoincrements on SQLite too.
BigPk = BigInteger().with_variant(Integer(), "sqlite")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    location: Mapped[str] = mapped_column(String(255), default="")
    rtsp_url: Mapped[str] = mapped_column(String(500))
    direction: Mapped[str] = mapped_column(String(50), default="")
    lane: Mapped[str] = mapped_column(String(50), default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Free-form tuning: fps, roi, speed_limit_kmh, meters_per_pixel, etc.
    config: Mapped[dict] = mapped_column(JsonCol, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Recognition(Base):
    __tablename__ = "recognitions"
    __table_args__ = (
        Index("ix_recognitions_camera_captured", "camera_id", "captured_at"),
        Index("ix_recognitions_captured_at", "captured_at"),
    )

    id: Mapped[int] = mapped_column(BigPk, primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), index=True)
    plate_text: Mapped[str] = mapped_column(String(20), index=True)
    plate_confidence: Mapped[float] = mapped_column(Float)
    ocr_raw: Mapped[str] = mapped_column(String(64), default="")
    vehicle_type: Mapped[str] = mapped_column(String(30), default="unknown")
    vehicle_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    direction: Mapped[str] = mapped_column(String(50), default="")
    track_id: Mapped[str] = mapped_column(String(64), default="")
    bbox: Mapped[dict] = mapped_column(JsonCol, default=dict)
    evidence_path: Mapped[str] = mapped_column(String(500), default="")
    plate_image_path: Mapped[str] = mapped_column(String(500), default="")
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    camera: Mapped[Camera] = relationship()


class WatchlistEntry(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plate_text: Mapped[str] = mapped_column(String(20), index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(BigPk, primary_key=True)
    recognition_id: Mapped[int] = mapped_column(ForeignKey("recognitions.id"), index=True)
    watchlist_id: Mapped[int | None] = mapped_column(
        ForeignKey("watchlist.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(30))  # watchlist | speed
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    message: Mapped[str] = mapped_column(Text, default="")
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    acknowledged_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    recognition: Mapped[Recognition] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigPk, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(50))
    resource: Mapped[str] = mapped_column(String(255))
    detail: Mapped[dict] = mapped_column(JsonCol, default=dict)
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

"""Toll-domain ORM models.

These share the ANPR platform's declarative ``Base`` so ``create_all`` (dev)
and Alembic (prod) build them alongside the recognition tables. Tables the
frontend edits get dedicated columns; free-form config blobs the frontend
reads/writes wholesale (system settings, RFID config, thresholds, comms) live
in a single key/value ``toll_settings`` table.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import BigPk, JsonCol
from app.db.session import Base


class FastagAccount(Base):
    __tablename__ = "toll_fastag_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tag_id: Mapped[str] = mapped_column(String(40), unique=True)
    plate: Mapped[str] = mapped_column(String(20), index=True)
    bank: Mapped[str] = mapped_column(String(40), default="")
    balance: Mapped[int] = mapped_column(Integer, default=0)
    # Active | Blacklisted | LowBalance
    status: Mapped[str] = mapped_column(String(20), default="Active")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TollTransaction(Base):
    __tablename__ = "toll_transactions"

    # Human-facing id e.g. TXN10200001 (kept as PK to match the frontend).
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    time: Mapped[str] = mapped_column(String(8), default="")   # HH:MM:SS
    lane: Mapped[str] = mapped_column(String(30), default="")
    reg: Mapped[str] = mapped_column(String(20), index=True)   # plate
    cls: Mapped[str] = mapped_column(String(30), default="Car / Jeep")
    tag: Mapped[str | None] = mapped_column(String(40), nullable=True)
    speed: Mapped[int] = mapped_column(Integer, default=0)
    amount: Mapped[int] = mapped_column(Integer, default=0)
    mode: Mapped[str] = mapped_column(String(20), default="")   # FASTag|Cash|Exempted|Violation
    status: Mapped[str] = mapped_column(String(20), default="")  # Paid|Failed|Pending|Exempted|Violation
    plate_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Link back to the source recognition (nullable for seeded/mock rows).
    recognition_id: Mapped[int | None] = mapped_column(BigPk, nullable=True)


class Vehicle(Base):
    __tablename__ = "toll_vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plate: Mapped[str] = mapped_column(String(20), unique=True)
    cls: Mapped[str] = mapped_column(String(30), default="Car / Jeep")
    owner: Mapped[str] = mapped_column(String(120), default="")
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TollRate(Base):
    __tablename__ = "toll_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(20), unique=True)   # car|lcv|bus|axle3|axle46|oversize
    label: Mapped[str] = mapped_column(String(60), default="")
    sub: Mapped[str] = mapped_column(String(60), default="")
    icon: Mapped[str] = mapped_column(String(8), default="")
    amount: Mapped[int] = mapped_column(Integer, default=0)


class Lane(Base):
    __tablename__ = "toll_lanes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(30), default="")
    direction: Mapped[str] = mapped_column(String(10), default="Entry")  # Entry|Exit
    speed: Mapped[int] = mapped_column(Integer, default=60)
    headway: Mapped[int] = mapped_column(Integer, default=10)
    toll: Mapped[int] = mapped_column(Integer, default=185)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Violation(Base):
    __tablename__ = "toll_violations"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # VIO-001
    vrn: Mapped[str] = mapped_column(String(20), index=True)
    date: Mapped[str] = mapped_column(String(10), default="")
    time: Mapped[str] = mapped_column(String(8), default="")
    lane: Mapped[str] = mapped_column(String(30), default="")
    type: Mapped[str] = mapped_column(String(40), default="")
    speed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fine: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="Pending")


class ReconRow(Base):
    """NPCI reconciliation / audit row (drives the Audit page)."""

    __tablename__ = "toll_recon"

    aid: Mapped[str] = mapped_column(String(20), primary_key=True)  # AUD200000
    txn: Mapped[str] = mapped_column(String(20), index=True)
    vrn: Mapped[str] = mapped_column(String(20), default="")
    amount: Mapped[int] = mapped_column(Integer, default=0)
    bank: Mapped[str] = mapped_column(String(40), default="")
    ref: Mapped[str] = mapped_column(String(40), default="")
    sent: Mapped[str] = mapped_column(String(40), default="")
    settled: Mapped[str] = mapped_column(String(40), default="")
    tag_bal: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(20), default="Success")


class AnprCameraCfg(Base):
    """ANPR/Surveillance camera *settings* rows (Configuration page)."""

    __tablename__ = "toll_anpr_cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), default="ANPR")  # ANPR|Surveillance
    lane: Mapped[str] = mapped_column(String(30), default="")
    role: Mapped[str] = mapped_column(String(10), default="Front")  # Front|Rear
    label: Mapped[str] = mapped_column(String(60), default="")
    zone: Mapped[str] = mapped_column(String(60), default="")
    ip: Mapped[str] = mapped_column(String(40), default="")
    resolution: Mapped[str] = mapped_column(String(20), default="1080P")
    framerate: Mapped[int] = mapped_column(Integer, default=25)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class TollUser(Base):
    """Toll operator/admin accounts (Admin + Configuration → Users pages).

    Separate from the ANPR platform ``users`` table so the two RBAC systems
    don't collide; the compat login authenticates against these rows.
    """

    __tablename__ = "toll_users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # uuid or slug
    name: Mapped[str] = mapped_column(String(120), default="")
    username: Mapped[str] = mapped_column(String(60), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    role: Mapped[str] = mapped_column(String(40), default="Operator")
    plaza: Mapped[str] = mapped_column(String(80), default="")
    hashed_password: Mapped[str] = mapped_column(String(255), default="")
    last: Mapped[str] = mapped_column(String(40), default="—")
    status: Mapped[str] = mapped_column(String(20), default="Active")  # Active|Inactive
    color: Mapped[str] = mapped_column(String(16), default="#2563eb")


class TollSetting(Base):
    """Key/value store for wholesale config blobs.

    Keys: ``system_settings``, ``rfid_config``, ``thresholds``, ``comm``.
    """

    __tablename__ = "toll_settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[dict] = mapped_column(JsonCol, default=dict)


class Notification(Base):
    __tablename__ = "toll_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(20), default="info")  # info|warn|error
    title: Mapped[str] = mapped_column(String(160), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    read: Mapped[bool] = mapped_column(Boolean, default=False)

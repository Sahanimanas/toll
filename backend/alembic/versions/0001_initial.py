"""Initial schema: users, cameras, recognitions, watchlist, alerts, audit_logs

Revision ID: 0001
Revises:
Create Date: 2026-07-04
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "cameras",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("location", sa.String(255), nullable=False, server_default=""),
        sa.Column("rtsp_url", sa.String(500), nullable=False),
        sa.Column("direction", sa.String(50), nullable=False, server_default=""),
        sa.Column("lane", sa.String(50), nullable=False, server_default=""),
        sa.Column("latitude", sa.Float),
        sa.Column("longitude", sa.Float),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "recognitions",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("camera_id", sa.Integer, sa.ForeignKey("cameras.id"), nullable=False),
        sa.Column("plate_text", sa.String(20), nullable=False),
        sa.Column("plate_confidence", sa.Float, nullable=False),
        sa.Column("ocr_raw", sa.String(64), nullable=False, server_default=""),
        sa.Column("vehicle_type", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("vehicle_confidence", sa.Float, nullable=False, server_default="0"),
        sa.Column("speed_kmh", sa.Float),
        sa.Column("direction", sa.String(50), nullable=False, server_default=""),
        sa.Column("track_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("bbox", JSONB, nullable=False, server_default="{}"),
        sa.Column("evidence_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("plate_image_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_recognitions_plate_text", "recognitions", ["plate_text"])
    op.create_index("ix_recognitions_captured_at", "recognitions", ["captured_at"])
    op.create_index("ix_recognitions_camera_id", "recognitions", ["camera_id"])
    op.create_index(
        "ix_recognitions_camera_captured", "recognitions", ["camera_id", "captured_at"]
    )

    op.create_table(
        "watchlist",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("plate_text", sa.String(20), nullable=False, index=True),
        sa.Column("reason", sa.Text, nullable=False, server_default=""),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column(
            "recognition_id",
            sa.BigInteger,
            sa.ForeignKey("recognitions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("watchlist_id", sa.Integer, sa.ForeignKey("watchlist.id")),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("message", sa.Text, nullable=False, server_default=""),
        sa.Column("acknowledged", sa.Boolean, nullable=False, server_default=sa.false(), index=True),
        sa.Column("acknowledged_by", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource", sa.String(255), nullable=False),
        sa.Column("detail", JSONB, nullable=False, server_default="{}"),
        sa.Column("ip", sa.String(64), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("alerts")
    op.drop_table("watchlist")
    op.drop_table("recognitions")
    op.drop_table("cameras")
    op.drop_table("users")

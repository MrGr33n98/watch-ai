"""Add expiring one-time pairing codes and hashed watch credentials.

Revision ID: 202611230003
Revises: 202611230002
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202611230003"
down_revision: str | None = "202611230002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pairing_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("expires_at > created_at", name="ck_pairing_code_expiration"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index(
        "ix_pairing_codes_user_expires_at",
        "pairing_codes",
        ["user_id", "expires_at"],
    )
    op.create_table(
        "watch_devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("device_name", sa.String(length=120), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "scope", sa.String(length=32), server_default="sessions:read", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("scope = 'sessions:read'", name="ck_watch_device_scope"),
        sa.CheckConstraint("expires_at > created_at", name="ck_watch_device_expiration"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_watch_devices_user_id", "watch_devices", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_watch_devices_user_id", table_name="watch_devices")
    op.drop_table("watch_devices")
    op.drop_index("ix_pairing_codes_user_expires_at", table_name="pairing_codes")
    op.drop_table("pairing_codes")

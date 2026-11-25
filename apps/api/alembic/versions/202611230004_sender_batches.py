"""Persist sender-to-session batch bindings and ordered image hashes.

Revision ID: 202611230004
Revises: 202611230003
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202611230004"
down_revision: str | None = "202611230003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("media_sha", sa.String(length=64), nullable=True))
    op.create_table(
        "sender_session_bindings",
        sa.Column("sender_hmac", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"], ["study_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("sender_hmac"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index(
        "ix_sender_session_bindings_expires_at",
        "sender_session_bindings",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sender_session_bindings_expires_at", table_name="sender_session_bindings"
    )
    op.drop_table("sender_session_bindings")
    op.drop_column("questions", "media_sha")

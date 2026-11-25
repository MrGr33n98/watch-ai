"""Add bounded retry leases and dead-letter state to outbox events.

Revision ID: 202611230005
Revises: 202611230004
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202611230005"
down_revision: str | None = "202611230004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "outbox_events",
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "outbox_events",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "outbox_events",
        sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "outbox_events",
        sa.Column("last_error_code", sa.String(length=48), nullable=True),
    )
    op.create_index(
        "ix_outbox_events_retry_due",
        "outbox_events",
        ["next_attempt_at", "published_at", "dead_lettered_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_events_retry_due", table_name="outbox_events")
    op.drop_column("outbox_events", "last_error_code")
    op.drop_column("outbox_events", "dead_lettered_at")
    op.drop_column("outbox_events", "locked_until")
    op.drop_column("outbox_events", "next_attempt_at")

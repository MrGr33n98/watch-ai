"""Persist provider-reported model costs for monthly budget accounting.

Revision ID: 202611240008
Revises: 202611240007
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202611240008"
down_revision: str | None = "202611240007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_usage_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=20, scale=12), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("cost_usd >= 0", name="ck_model_usage_cost_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_model_usage_records_recorded_at",
        "model_usage_records",
        ["recorded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_model_usage_records_recorded_at", table_name="model_usage_records")
    op.drop_table("model_usage_records")

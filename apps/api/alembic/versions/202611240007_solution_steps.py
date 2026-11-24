"""Persist typed, ordered solution steps for watch presentation.

Revision ID: 202611240007
Revises: 202611230006
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202611240007"
down_revision: str | None = "202611230006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "solution_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.SmallInteger(), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("plain_text", sa.String(), nullable=False),
        sa.Column("latex", sa.String(), nullable=True),
        sa.Column("render_url", sa.String(length=512), nullable=True),
        sa.Column("alt_text", sa.String(), nullable=True),
        sa.Column("verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint("ordinal >= 1", name="ck_solution_step_ordinal"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", "ordinal", name="uq_solution_steps_question_ordinal"),
    )


def downgrade() -> None:
    op.drop_table("solution_steps")

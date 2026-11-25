"""Record which ordered question accepted each inbound exercise image.

Revision ID: 202611230006
Revises: 202611230005
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202611230006"
down_revision: str | None = "202611230005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "inbound_messages",
        sa.Column("question_ordinal", sa.SmallInteger(), nullable=True),
    )
    op.create_check_constraint(
        "ck_inbound_question_ordinal",
        "inbound_messages",
        "question_ordinal IS NULL OR question_ordinal BETWEEN 1 AND 4",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_inbound_question_ordinal", "inbound_messages", type_="check"
    )
    op.drop_column("inbound_messages", "question_ordinal")

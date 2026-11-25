"""Uncap question and session cardinality limits for multi-question sheets.

Revision ID: 202611250001
Revises: 202611240008
Create Date: 2026-11-25
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202611250001"
down_revision: str | None = "202611240008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_session_expected_count", "study_sessions", type_="check")
    op.create_check_constraint(
        "ck_session_expected_count",
        "study_sessions",
        "expected_count >= 1",
    )
    op.drop_constraint("ck_session_received_count", "study_sessions", type_="check")
    op.create_check_constraint(
        "ck_session_received_count",
        "study_sessions",
        "received_count >= 0",
    )
    op.drop_constraint("ck_question_ordinal", "questions", type_="check")
    op.create_check_constraint(
        "ck_question_ordinal",
        "questions",
        "ordinal >= 1",
    )


def downgrade() -> None:
    op.drop_constraint("ck_session_expected_count", "study_sessions", type_="check")
    op.create_check_constraint(
        "ck_session_expected_count",
        "study_sessions",
        "expected_count BETWEEN 1 AND 4",
    )
    op.drop_constraint("ck_session_received_count", "study_sessions", type_="check")
    op.create_check_constraint(
        "ck_session_received_count",
        "study_sessions",
        "received_count BETWEEN 0 AND 4",
    )
    op.drop_constraint("ck_question_ordinal", "questions", type_="check")
    op.create_check_constraint(
        "ck_question_ordinal",
        "questions",
        "ordinal BETWEEN 1 AND 4",
    )


"""Initial users, study sessions, and ordered questions.

Revision ID: 202611230001
Revises:
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202611230001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_table(
        "study_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="created", nullable=False),
        sa.Column("expected_count", sa.SmallInteger(), server_default=sa.text("4"), nullable=False),
        sa.Column("received_count", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint("expected_count BETWEEN 1 AND 4", name="ck_session_expected_count"),
        sa.CheckConstraint("received_count BETWEEN 0 AND 4", name="ck_session_received_count"),
        sa.CheckConstraint(
            "received_count <= expected_count", name="ck_session_received_le_expected"
        ),
        sa.CheckConstraint(
            "status IN ('created', 'collecting', 'queued', 'processing', 'ready', "
            "'partial', 'needs_review', 'failed', 'cancelled', 'expired')",
            name="ck_session_status",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_study_sessions_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_study_sessions"),
    )
    op.create_index(
        "ix_study_sessions_user_created_at",
        "study_sessions",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="uploaded", nullable=False),
        sa.Column("statement_text", sa.String(), nullable=True),
        sa.Column("problem_type", sa.String(length=80), nullable=True),
        sa.Column("confidence", sa.String(length=12), nullable=True),
        sa.Column(
            "verification_status", sa.String(length=16), server_default="unverified", nullable=False
        ),
        sa.Column("final_answer", sa.String(), nullable=True),
        sa.Column("units", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("ordinal BETWEEN 1 AND 4", name="ck_question_ordinal"),
        sa.CheckConstraint(
            "status IN ('uploaded', 'validating', 'interpreting', 'solving', "
            "'ready', 'needs_review', 'failed')",
            name="ck_question_status",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR confidence IN ('high', 'medium', 'low')",
            name="ck_question_confidence",
        ),
        sa.CheckConstraint(
            "verification_status IN ('verified', 'unverified', 'inconclusive', 'rejected')",
            name="ck_question_verification_status",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["study_sessions.id"],
            name="fk_questions_session_id_study_sessions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_questions"),
        sa.UniqueConstraint("session_id", "ordinal", name="uq_questions_session_ordinal"),
    )


def downgrade() -> None:
    op.drop_table("questions")
    op.drop_index("ix_study_sessions_user_created_at", table_name="study_sessions")
    op.drop_table("study_sessions")
    op.drop_table("users")

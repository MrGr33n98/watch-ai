from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.adapters.db.base import Base


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list[StudySessionRecord]] = relationship(back_populates="user")


class StudySessionRecord(Base):
    __tablename__ = "study_sessions"
    __table_args__ = (
        CheckConstraint("expected_count >= 1", name="ck_session_expected_count"),
        CheckConstraint("received_count >= 0", name="ck_session_received_count"),
        CheckConstraint("received_count <= expected_count", name="ck_session_received_le_expected"),
        CheckConstraint(
            "status IN ('created', 'collecting', 'queued', 'processing', 'ready', "
            "'partial', 'needs_review', 'failed', 'cancelled', 'expired')",
            name="ck_session_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="created", server_default="created"
    )
    expected_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=4, server_default=text("4")
    )
    received_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default=text("1")
    )

    user: Mapped[UserRecord] = relationship(back_populates="sessions")
    questions: Mapped[list[QuestionRecord]] = relationship(
        back_populates="session",
        order_by="QuestionRecord.ordinal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    sender_binding: Mapped[SenderSessionBindingRecord | None] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )


class QuestionRecord(Base):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint("session_id", "ordinal", name="uq_questions_session_ordinal"),
        CheckConstraint("ordinal >= 1", name="ck_question_ordinal"),
        CheckConstraint(
            "status IN ('uploaded', 'validating', 'interpreting', 'solving', "
            "'ready', 'needs_review', 'failed')",
            name="ck_question_status",
        ),
        CheckConstraint(
            "confidence IS NULL OR confidence IN ('high', 'medium', 'low')",
            name="ck_question_confidence",
        ),
        CheckConstraint(
            "verification_status IN ('verified', 'unverified', 'inconclusive', 'rejected')",
            name="ck_question_verification_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("study_sessions.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="uploaded", server_default="uploaded"
    )
    statement_text: Mapped[str | None] = mapped_column(String)
    media_sha: Mapped[str | None] = mapped_column(String(64))
    problem_type: Mapped[str | None] = mapped_column(String(80))
    confidence: Mapped[str | None] = mapped_column(String(12))
    verification_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unverified", server_default="unverified"
    )
    final_answer: Mapped[str | None] = mapped_column(String)
    units: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    session: Mapped[StudySessionRecord] = relationship(back_populates="questions")
    steps: Mapped[list[SolutionStepRecord]] = relationship(
        back_populates="question",
        order_by="SolutionStepRecord.ordinal",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class SolutionStepRecord(Base):
    __tablename__ = "solution_steps"
    __table_args__ = (
        UniqueConstraint("question_id", "ordinal", name="uq_solution_steps_question_ordinal"),
        CheckConstraint("ordinal >= 1", name="ck_solution_step_ordinal"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    question_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    plain_text: Mapped[str] = mapped_column(String, nullable=False)
    latex: Mapped[str | None] = mapped_column(String)
    render_url: Mapped[str | None] = mapped_column(String(512))
    alt_text: Mapped[str | None] = mapped_column(String)
    verified: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    question: Mapped[QuestionRecord] = relationship(back_populates="steps")


class SenderSessionBindingRecord(Base):
    __tablename__ = "sender_session_bindings"
    __table_args__ = (Index("ix_sender_session_bindings_expires_at", "expires_at"),)

    sender_hmac: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("study_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    session: Mapped[StudySessionRecord] = relationship(back_populates="sender_binding")


class InboundMessageRecord(Base):
    __tablename__ = "inbound_messages"
    __table_args__ = (
        UniqueConstraint("provider", "provider_message_id", name="uq_inbound_provider_message"),
        CheckConstraint(
            "state IN ('received', 'queued', 'processing', 'processed', 'rejected', 'failed')",
            name="ck_inbound_message_state",
        ),
        Index("ix_inbound_messages_state_received_at", "state", "received_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_message_id: Mapped[str] = mapped_column(String(160), nullable=False)
    sender_hmac: Mapped[str] = mapped_column(String(128), nullable=False)
    media_sha: Mapped[str | None] = mapped_column(String(64))
    session_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("study_sessions.id", ondelete="SET NULL")
    )
    question_ordinal: Mapped[int | None] = mapped_column(SmallInteger)
    state: Mapped[str] = mapped_column(
        String(24), nullable=False, default="received", server_default="received"
    )
    provider_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OutboxEventRecord(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        CheckConstraint("attempt_count >= 0", name="ck_outbox_attempt_count"),
        Index("ix_outbox_events_published_at", "published_at"),
        Index("ix_outbox_events_aggregate", "aggregate_type", "aggregate_id"),
        Index(
            "ix_outbox_events_retry_due",
            "next_attempt_at",
            "published_at",
            "dead_lettered_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default=text("0")
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dead_lettered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(48))


class ModelUsageRecord(Base):
    __tablename__ = "model_usage_records"
    __table_args__ = (
        CheckConstraint("cost_usd >= 0", name="ck_model_usage_cost_nonnegative"),
        Index("ix_model_usage_records_recorded_at", "recorded_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(20, 12), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PairingCodeRecord(Base):
    __tablename__ = "pairing_codes"
    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="ck_pairing_code_expiration"),
        Index("ix_pairing_codes_user_expires_at", "user_id", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WatchDeviceRecord(Base):
    __tablename__ = "watch_devices"
    __table_args__ = (
        CheckConstraint("scope = 'sessions:read'", name="ck_watch_device_scope"),
        CheckConstraint("expires_at > created_at", name="ck_watch_device_expiration"),
        Index("ix_watch_devices_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    device_name: Mapped[str] = mapped_column(String(120), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    scope: Mapped[str] = mapped_column(
        String(32), nullable=False, default="sessions:read", server_default="sessions:read"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Index(
    "ix_study_sessions_user_created_at",
    StudySessionRecord.user_id,
    StudySessionRecord.created_at.desc(),
)

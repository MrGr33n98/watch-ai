"""Session aggregate with ordered questions and explicit lifecycle rules."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class SessionDomainError(ValueError):
    """Base error for invalid session state or input."""


class InvalidExpectedQuestionCount(SessionDomainError):
    """Raised when the requested batch size is outside the supported range."""


class TooManyQuestions(SessionDomainError):
    """Raised when an item would exceed the expected batch size or hard limit."""


class EmptySession(SessionDomainError):
    """Raised when an empty session is queued for interpretation."""


class InvalidSessionTransition(SessionDomainError):
    """Raised when a session attempts a transition outside its lifecycle."""


class InvalidQuestionTransition(SessionDomainError):
    """Raised when a question attempts a transition outside its lifecycle."""


class QuestionNotFound(SessionDomainError):
    """Raised when a question ordinal does not exist in the session."""


class StepsRequired(SessionDomainError):
    """Raised when a question is marked ready without validated solution steps."""


class SessionStatus(StrEnum):
    CREATED = "created"
    COLLECTING = "collecting"
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    PARTIAL = "partial"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class QuestionStatus(StrEnum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    INTERPRETING = "interpreting"
    SOLVING = "solving"
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


@dataclass(frozen=True, slots=True, order=True)
class QuestionOrder:
    """One-based display and arrival order within a session."""

    value: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.value, bool)
            or not isinstance(self.value, int)
            or self.value < 1
        ):
            raise ValueError("Question order must be at least 1")


@dataclass(frozen=True, slots=True)
class QuestionItem:
    """A question attached to one ordered image in a study session."""

    id: UUID
    order: QuestionOrder
    media_sha: str
    status: QuestionStatus = QuestionStatus.UPLOADED
    validated_step_ids: tuple[UUID, ...] = ()

    def __post_init__(self) -> None:
        if not self.media_sha.strip():
            raise ValueError("Question media SHA must not be empty")
        if self.status is QuestionStatus.READY and not self.validated_step_ids:
            raise StepsRequired("A ready question must reference validated solution steps")

    @property
    def ordinal(self) -> int:
        return self.order.value


_SESSION_TRANSITIONS: dict[SessionStatus, frozenset[SessionStatus]] = {
    SessionStatus.CREATED: frozenset(
        {SessionStatus.COLLECTING, SessionStatus.CANCELLED, SessionStatus.EXPIRED}
    ),
    SessionStatus.COLLECTING: frozenset(
        {SessionStatus.QUEUED, SessionStatus.CANCELLED, SessionStatus.EXPIRED}
    ),
    SessionStatus.QUEUED: frozenset(
        {SessionStatus.PROCESSING, SessionStatus.CANCELLED, SessionStatus.EXPIRED}
    ),
    SessionStatus.PROCESSING: frozenset(
        {
            SessionStatus.READY,
            SessionStatus.PARTIAL,
            SessionStatus.NEEDS_REVIEW,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
            SessionStatus.EXPIRED,
        }
    ),
}

_QUESTION_TRANSITIONS: dict[QuestionStatus, frozenset[QuestionStatus]] = {
    QuestionStatus.UPLOADED: frozenset(
        {QuestionStatus.VALIDATING, QuestionStatus.NEEDS_REVIEW, QuestionStatus.FAILED}
    ),
    QuestionStatus.VALIDATING: frozenset(
        {QuestionStatus.INTERPRETING, QuestionStatus.NEEDS_REVIEW, QuestionStatus.FAILED}
    ),
    QuestionStatus.INTERPRETING: frozenset(
        {QuestionStatus.SOLVING, QuestionStatus.NEEDS_REVIEW, QuestionStatus.FAILED}
    ),
    QuestionStatus.SOLVING: frozenset(
        {QuestionStatus.NEEDS_REVIEW, QuestionStatus.FAILED}
    ),
}

_TERMINAL_QUESTION_STATUSES = frozenset(
    {QuestionStatus.READY, QuestionStatus.NEEDS_REVIEW, QuestionStatus.FAILED}
)
_TERMINAL_SESSION_STATUSES = frozenset(
    {
        SessionStatus.READY,
        SessionStatus.PARTIAL,
        SessionStatus.NEEDS_REVIEW,
        SessionStatus.FAILED,
        SessionStatus.CANCELLED,
        SessionStatus.EXPIRED,
    }
)


@dataclass(slots=True)
class StudySession:
    """Aggregate root enforcing question ordering, count, and lifecycle."""

    expected_count: int = 4
    id: UUID = field(default_factory=uuid4)
    status: SessionStatus = SessionStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    _questions: list[QuestionItem] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self._validate_expected_count(self.expected_count)
        if not isinstance(self.status, SessionStatus):
            raise ValueError("Session status must be a SessionStatus")
        if self.created_at.utcoffset() is None:
            raise ValueError("Session timestamps must be timezone-aware")
        if self.completed_at is not None and self.completed_at.utcoffset() is None:
            raise ValueError("Session timestamps must be timezone-aware")
        if len(self._questions) > self.expected_count:
            raise TooManyQuestions("Session contains more questions than expected")
        expected_ordinals = list(range(1, len(self._questions) + 1))
        if [question.ordinal for question in self._questions] != expected_ordinals:
            raise ValueError("Questions must have contiguous arrival order starting at 1")

    @classmethod
    def new(cls, expected_count: int = 4) -> StudySession:
        """Create an empty session ready to receive its first question."""
        cls._validate_expected_count(expected_count)
        return cls(expected_count=expected_count)

    @property
    def questions(self) -> tuple[QuestionItem, ...]:
        """Return an immutable view so callers cannot bypass aggregate rules."""
        return tuple(self._questions)

    @property
    def received_count(self) -> int:
        return len(self._questions)

    def attach_question(self, media_sha: str) -> QuestionItem:
        """Attach a question in arrival order; reaching the target queues the batch."""
        if len(self._questions) >= self.expected_count:
            raise TooManyQuestions("Session already contains its maximum question count")
        if self.status not in {SessionStatus.CREATED, SessionStatus.COLLECTING}:
            raise InvalidSessionTransition("Questions can only be attached while collecting")
        if not media_sha.strip():
            raise ValueError("Question media SHA must not be empty")

        if self.status is SessionStatus.CREATED:
            self._transition(SessionStatus.COLLECTING)

        question = QuestionItem(
            id=uuid4(),
            order=QuestionOrder(len(self._questions) + 1),
            media_sha=media_sha,
        )
        self._questions.append(question)
        if self.received_count == self.expected_count:
            self.queue()
        return question

    def queue(self) -> None:
        """Close collection and enqueue a non-empty batch, including a short batch."""
        if not self._questions:
            raise EmptySession("An empty session cannot be queued")
        self._transition(SessionStatus.QUEUED)

    def start_processing(self) -> None:
        self._transition(SessionStatus.PROCESSING)

    def transition_to(self, target: SessionStatus, *, at: datetime | None = None) -> None:
        """Apply an explicit non-result transition such as cancellation or expiry."""
        if target in {
            SessionStatus.READY,
            SessionStatus.PARTIAL,
            SessionStatus.NEEDS_REVIEW,
            SessionStatus.FAILED,
        }:
            raise InvalidSessionTransition("Result status is derived from question outcomes")
        self._transition(target, at=at)

    def advance_question(
        self,
        ordinal: int,
        target: QuestionStatus,
        *,
        at: datetime | None = None,
    ) -> QuestionItem:
        """Move an in-flight question through validation, interpretation, and solving."""
        if self.status is not SessionStatus.PROCESSING:
            raise InvalidSessionTransition("Questions can only advance while processing")
        question_index = self._question_index(ordinal)
        question = self._questions[question_index]
        if target not in _QUESTION_TRANSITIONS.get(question.status, frozenset()):
            raise InvalidQuestionTransition(
                f"Cannot move question from {question.status.value} to {target.value}"
            )
        updated = replace(question, status=target)
        self._questions[question_index] = updated
        self._finish_if_all_questions_terminal(at=at)
        return updated

    def mark_question_ready(
        self,
        ordinal: int,
        *,
        validated_step_ids: tuple[UUID, ...],
        at: datetime | None = None,
    ) -> QuestionItem:
        """Mark a solved question ready only when validated step references exist."""
        if self.status is not SessionStatus.PROCESSING:
            raise InvalidSessionTransition("Questions can only advance while processing")
        if not validated_step_ids:
            raise StepsRequired("A ready question must reference validated solution steps")
        question_index = self._question_index(ordinal)
        question = self._questions[question_index]
        if question.status is not QuestionStatus.SOLVING:
            raise InvalidQuestionTransition("A question must be solving before it can be ready")
        updated = replace(
            question,
            status=QuestionStatus.READY,
            validated_step_ids=tuple(validated_step_ids),
        )
        self._questions[question_index] = updated
        self._finish_if_all_questions_terminal(at=at)
        return updated

    def mark_question_needs_review(
        self,
        ordinal: int,
        *,
        at: datetime | None = None,
    ) -> QuestionItem:
        """Stop an ambiguous or unsupported question without inventing an answer."""
        return self.advance_question(ordinal, QuestionStatus.NEEDS_REVIEW, at=at)

    def mark_question_failed(
        self,
        ordinal: int,
        *,
        at: datetime | None = None,
    ) -> QuestionItem:
        """Record a question processing failure and derive the session outcome."""
        return self.advance_question(ordinal, QuestionStatus.FAILED, at=at)

    @staticmethod
    def _validate_expected_count(expected_count: int) -> None:
        if (
            isinstance(expected_count, bool)
            or not isinstance(expected_count, int)
            or expected_count < 1
        ):
            raise InvalidExpectedQuestionCount("Expected question count must be at least 1")

    def _question_index(self, ordinal: int) -> int:
        if isinstance(ordinal, bool) or not 1 <= ordinal <= self.received_count:
            raise QuestionNotFound(f"Question {ordinal} does not exist in this session")
        return ordinal - 1

    def _finish_if_all_questions_terminal(self, *, at: datetime | None = None) -> None:
        if not self._questions or any(
            question.status not in _TERMINAL_QUESTION_STATUSES for question in self._questions
        ):
            return

        statuses = [question.status for question in self._questions]
        if QuestionStatus.NEEDS_REVIEW in statuses:
            result = SessionStatus.NEEDS_REVIEW
        elif all(status is QuestionStatus.READY for status in statuses):
            result = (
                SessionStatus.READY
                if self.received_count == self.expected_count
                else SessionStatus.PARTIAL
            )
        elif all(status is QuestionStatus.FAILED for status in statuses):
            result = SessionStatus.FAILED
        else:
            result = SessionStatus.PARTIAL
        self._transition(result, at=at)

    def _transition(self, target: SessionStatus, *, at: datetime | None = None) -> None:
        allowed = _SESSION_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise InvalidSessionTransition(
                f"Cannot move session from {self.status.value} to {target.value}"
            )
        if target in {
            SessionStatus.READY,
            SessionStatus.PARTIAL,
            SessionStatus.NEEDS_REVIEW,
            SessionStatus.FAILED,
        } and self.status is not SessionStatus.PROCESSING:
            raise InvalidSessionTransition("A result status can only follow processing")
        if target in _TERMINAL_SESSION_STATUSES and at is not None and at.utcoffset() is None:
            raise ValueError("Session timestamps must be timezone-aware")

        self.status = target
        if target in _TERMINAL_SESSION_STATUSES:
            self.completed_at = at or datetime.now(UTC)

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SessionSummaryRead:
    id: UUID
    status: str
    received_count: int
    expected_count: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class QuestionSummaryRead:
    id: UUID
    ordinal: int
    status: str
    title: str | None
    result_preview: str | None


@dataclass(frozen=True, slots=True)
class StudySessionRead(SessionSummaryRead):
    questions: tuple[QuestionSummaryRead, ...]


@dataclass(frozen=True, slots=True)
class SolutionStepRead:
    ordinal: int
    kind: str
    title: str
    plain_text: str
    latex: str | None
    render_url: str | None
    alt_text: str | None
    verified: bool


@dataclass(frozen=True, slots=True)
class QuestionDetailRead(QuestionSummaryRead):
    statement: str
    verified: bool
    verification_status: str
    final_answer: str | None
    units: str | None
    steps: tuple[SolutionStepRead, ...]


class SessionQueryRepository(Protocol):
    def list_sessions(self, owner_id: UUID, limit: int) -> Sequence[SessionSummaryRead]: ...

    def get_session(self, owner_id: UUID, session_id: UUID) -> StudySessionRead | None: ...

    def get_question(
        self,
        owner_id: UUID,
        session_id: UUID,
        ordinal: int,
    ) -> QuestionDetailRead | None: ...


class SessionQueries:
    def __init__(self, repository: SessionQueryRepository) -> None:
        self._repository = repository

    def list_sessions(self, owner_id: UUID, limit: int) -> Sequence[SessionSummaryRead]:
        return self._repository.list_sessions(owner_id, limit)

    def get_session(self, owner_id: UUID, session_id: UUID) -> StudySessionRead | None:
        return self._repository.get_session(owner_id, session_id)

    def get_question(
        self,
        owner_id: UUID,
        session_id: UUID,
        ordinal: int,
    ) -> QuestionDetailRead | None:
        return self._repository.get_question(owner_id, session_id, ordinal)

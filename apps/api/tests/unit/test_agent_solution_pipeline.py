from __future__ import annotations

from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.db.base import Base
from app.adapters.db.models import (
    QuestionRecord,
    SolutionStepRecord,
    StudySessionRecord,
    UserRecord,
)
from app.adapters.db.session_queries import SqlAlchemySessionQueryRepository
from app.adapters.db.solutions import SqlAlchemySolutionRepository
from app.application.problem_mapper import StructuredProblemMapper
from app.application.solution_pipeline import SolutionPipeline
from app.application.solution_policy import SolutionPolicy
from app.domain.ingestion.models import InboundMessage
from app.domain.interpretation.models import (
    InterpretationConfidence,
    InterpretedExercise,
    InterpretedStep,
)
from app.domain.math_verification.solution import SolutionStatus


class MockAgentVisionProvider:
    def __init__(self, exercise: InterpretedExercise) -> None:
        self.exercise = exercise

    def interpret(self, message: InboundMessage, *, image_bytes: bytes) -> InterpretedExercise:
        del message, image_bytes
        return self.exercise


class MemorySolutionRepository:
    def __init__(self) -> None:
        self.saved_solutions: list[tuple[InboundMessage, InterpretedExercise, object]] = []

    def save_solution(
        self,
        message: InboundMessage,
        exercise: InterpretedExercise,
        result: object,
    ) -> None:
        self.saved_solutions.append((message, exercise, result))


def test_pipeline_adopts_agent_steps_for_unsupported_operation() -> None:
    agent_steps = (
        InterpretedStep(
            ordinal=1,
            kind="formula",
            title="Equação de Bernoulli",
            plain_text="p1 + 0.5*rho*v1^2 = p2 + 0.5*rho*v2^2",
            latex=r"p_1 + \frac{1}{2}\rho v_1^2 = p_2 + \frac{1}{2}\rho v_2^2",
        ),
        InterpretedStep(
            ordinal=2,
            kind="calculation",
            title="Cálculo da Pressão",
            plain_text="p2 = 101325 - 500 = 100825 Pa",
            latex=r"p_2 = 100825\ \mathrm{Pa}",
        ),
        InterpretedStep(
            ordinal=3,
            kind="result",
            title="Resposta Final",
            plain_text="100825 Pa",
            latex=r"\boxed{p_2 = 100825\ \mathrm{Pa}}",
        ),
    )
    exercise = InterpretedExercise(
        statement="Calcule a pressão no ponto 2 usando Bernoulli.",
        problem_type="fluid mechanics",
        confidence=InterpretationConfidence.HIGH,
        needs_review=False,
        solution_steps=agent_steps,
        final_answer="100825",
        units="Pa",
    )
    repo = MemorySolutionRepository()
    pipeline = SolutionPipeline(
        vision_provider=MockAgentVisionProvider(exercise),
        problem_mapper=StructuredProblemMapper(),
        solution_policy=SolutionPolicy(),
        result_repository=repo,
    )
    message = InboundMessage(
        provider="waha",
        provider_message_id="msg-1",
        sender_hmac="hmac-1",
        question_ordinal=1,
    )

    result = pipeline.process(message, image_bytes=b"dummy")

    assert result.status is SolutionStatus.READY
    assert result.verified is False
    assert result.verification_status == "unverified"
    assert result.final_answer == "100825"
    assert result.units == "Pa"
    assert len(result.steps) == 3
    assert result.steps[0].title == "Equação de Bernoulli"
    assert result.steps[1].kind.value == "calculation"


def test_solutions_repository_and_queries_retain_unverified_calculations() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            UserRecord.__table__,
            StudySessionRecord.__table__,
            QuestionRecord.__table__,
            SolutionStepRecord.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    owner_id = uuid4()
    session_id = uuid4()

    with session_factory.begin() as db:
        user = UserRecord(id=owner_id)
        study_session = StudySessionRecord(
            id=session_id,
            user=user,
            status="collecting",
            expected_count=1,
            received_count=1,
        )
        question = QuestionRecord(
            id=uuid4(),
            session_id=session_id,
            ordinal=1,
            status="uploaded",
        )
        db.add_all([user, study_session, question])

    agent_steps = (
        InterpretedStep(
            ordinal=1,
            kind="formula",
            title="Equação",
            plain_text="f(x) = u^5",
            latex=r"f(u) = u^5",
        ),
        InterpretedStep(
            ordinal=2,
            kind="calculation",
            title="Cálculo",
            plain_text="df/dx = 30x(3x^2+2)^4",
            latex=r"30x(3x^2+2)^4",
        ),
        InterpretedStep(
            ordinal=3,
            kind="result",
            title="Resposta",
            plain_text="30x(3x^2+2)^4",
            latex=r"\boxed{30x(3x^2+2)^4}",
        ),
    )
    exercise = InterpretedExercise(
        statement="Derive f(x) = (3x^2+2)^5",
        problem_type="calculus",
        confidence=InterpretationConfidence.HIGH,
        needs_review=False,
        solution_steps=agent_steps,
        final_answer="30x(3x^2+2)^4",
        units=None,
    )
    message = InboundMessage(
        provider="waha",
        provider_message_id="msg-1",
        sender_hmac="hmac-1",
        session_id=session_id,
        question_ordinal=1,
    )
    pipeline = SolutionPipeline(
        vision_provider=MockAgentVisionProvider(exercise),
        problem_mapper=StructuredProblemMapper(),
        solution_policy=SolutionPolicy(),
        result_repository=SqlAlchemySolutionRepository(session_factory),
    )
    pipeline.process(message, image_bytes=b"dummy")

    with session_factory() as session:
        query_repo = SqlAlchemySessionQueryRepository(session)
        detail = query_repo.get_question(owner_id, session_id, 1)

    assert detail is not None
    assert detail.status == "ready"
    assert detail.verified is False
    assert detail.verification_status == "unverified"
    assert detail.final_answer == "30x(3x^2+2)^4"
    assert len(detail.steps) == 3
    assert [s.kind for s in detail.steps] == ["formula", "calculation", "result"]
    assert detail.steps[1].plain_text == "df/dx = 30x(3x^2+2)^4"

    engine.dispose()

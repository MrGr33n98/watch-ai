from uuid import uuid4

import pytest

from app.domain.sessions.models import (
    InvalidExpectedQuestionCount,
    InvalidQuestionTransition,
    InvalidSessionTransition,
    QuestionStatus,
    SessionStatus,
    StepsRequired,
    StudySession,
    TooManyQuestions,
)


@pytest.mark.parametrize("expected_count", [1, 2, 3, 4])
def test_sessions_preserve_question_order_and_queue_at_expected_count(
    expected_count: int,
) -> None:
    session = StudySession.new(expected_count=expected_count)

    questions = [
        session.attach_question(media_sha=f"sha{index}")
        for index in range(expected_count)
    ]

    assert [question.ordinal for question in questions] == list(range(1, expected_count + 1))
    assert [question.ordinal for question in session.questions] == list(
        range(1, expected_count + 1)
    )
    assert session.status is SessionStatus.QUEUED


@pytest.mark.parametrize("expected_count", [0, 5, -1, 1.5, True])
def test_session_rejects_expected_question_counts_outside_one_to_four(
    expected_count: int,
) -> None:
    with pytest.raises(InvalidExpectedQuestionCount):
        StudySession.new(expected_count=expected_count)


def test_session_rejects_a_fifth_question_without_replacing_existing_items() -> None:
    session = StudySession.new(expected_count=4)
    for index in range(4):
        session.attach_question(media_sha=f"sha{index}")

    with pytest.raises(TooManyQuestions):
        session.attach_question(media_sha="sha5")

    assert [question.media_sha for question in session.questions] == [
        "sha0",
        "sha1",
        "sha2",
        "sha3",
    ]


def test_session_finishes_ready_only_after_each_question_has_validated_steps() -> None:
    session = StudySession.new(expected_count=1)
    session.attach_question(media_sha="sha1")
    session.start_processing()
    session.advance_question(1, QuestionStatus.VALIDATING)
    session.advance_question(1, QuestionStatus.INTERPRETING)
    session.advance_question(1, QuestionStatus.SOLVING)

    with pytest.raises(StepsRequired):
        session.mark_question_ready(1, validated_step_ids=())

    session.mark_question_ready(1, validated_step_ids=(uuid4(),))

    assert session.questions[0].status is QuestionStatus.READY
    assert session.status is SessionStatus.READY
    assert session.completed_at is not None


def test_session_finishes_needs_review_for_an_ambiguous_question() -> None:
    session = StudySession.new(expected_count=1)
    session.attach_question(media_sha="sha1")
    session.start_processing()
    session.advance_question(1, QuestionStatus.VALIDATING)
    session.mark_question_needs_review(1)

    assert session.questions[0].status is QuestionStatus.NEEDS_REVIEW
    assert session.status is SessionStatus.NEEDS_REVIEW
    assert session.completed_at is not None


def test_session_rejects_skipped_lifecycle_transitions() -> None:
    session = StudySession.new(expected_count=1)

    with pytest.raises(InvalidSessionTransition):
        session.start_processing()

    session.attach_question(media_sha="sha1")
    session.start_processing()

    with pytest.raises(InvalidSessionTransition):
        session.transition_to(SessionStatus.COLLECTING)

    with pytest.raises(InvalidQuestionTransition):
        session.advance_question(1, QuestionStatus.READY)

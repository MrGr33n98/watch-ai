from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.adapters.db.retention import SqlAlchemySessionRetentionRepository
from app.adapters.db.session_queries import SqlAlchemySessionQueryRepository
from app.adapters.http.auth import WatchPrincipal, require_watch_principal
from app.adapters.http.database import DatabaseSession
from app.adapters.renderer.formulas import FormulaRenderer, PrivateFormulaAssetStore
from app.application.retention import SessionRetentionService
from app.application.session_queries import SessionQueries

router = APIRouter(prefix="/v1/sessions", tags=["watch"])


class SessionSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    received_count: int = Field(ge=0, le=4)
    expected_count: int = Field(ge=1, le=4)
    created_at: datetime


class QuestionSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ordinal: int = Field(ge=1, le=4)
    status: str
    title: str | None = None
    result_preview: str | None = None


class SessionListResponse(BaseModel):
    items: list[SessionSummaryResponse]
    next_cursor: str | None = None


class ApiErrorResponse(BaseModel):
    code: str
    message: str
    correlation_id: str | None


class StudySessionResponse(SessionSummaryResponse):
    questions: list[QuestionSummaryResponse] = Field(max_length=4)


class SolutionStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ordinal: int = Field(ge=1)
    kind: str
    title: str
    plain_text: str
    latex: str | None = None
    render_url: str | None = None
    alt_text: str | None = None
    verified: bool


class QuestionDetailResponse(QuestionSummaryResponse):
    statement: str
    verified: bool
    verification_status: str
    final_answer: str | None = None
    units: str | None = None
    steps: list[SolutionStepResponse]


@router.get(
    "",
    response_model=SessionListResponse,
    operation_id="listSessions",
    responses={401: {"model": ApiErrorResponse, "description": "Unauthorized"}},
)
def list_sessions(
    database: DatabaseSession,
    principal: Annotated[WatchPrincipal, Depends(require_watch_principal)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> SessionListResponse:
    queries = SessionQueries(SqlAlchemySessionQueryRepository(database))
    items = [
        SessionSummaryResponse.model_validate(item)
        for item in queries.list_sessions(principal.user_id, limit)
    ]
    return SessionListResponse(items=list(items), next_cursor=None)


@router.get(
    "/{session_id}",
    response_model=StudySessionResponse,
    operation_id="getSession",
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Not found"},
    },
)
def get_session(
    session_id: UUID,
    database: DatabaseSession,
    principal: Annotated[WatchPrincipal, Depends(require_watch_principal)],
) -> StudySessionResponse:
    queries = SessionQueries(SqlAlchemySessionQueryRepository(database))
    result = queries.get_session(principal.user_id, session_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return StudySessionResponse.model_validate(result)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteSession",
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Not found"},
    },
)
def delete_session(
    session_id: UUID,
    request: Request,
    database: DatabaseSession,
    principal: Annotated[WatchPrincipal, Depends(require_watch_principal)],
) -> Response:
    retention = SessionRetentionService(
        SqlAlchemySessionRetentionRepository(database),
        request.app.state.waha_media_store,
        request.app.state.session_retention_policy,
    )
    if not retention.delete_session(principal.user_id, session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{session_id}/questions/{ordinal}",
    response_model=QuestionDetailResponse,
    operation_id="getQuestion",
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Not found"},
    },
)
def get_question(
    session_id: UUID,
    ordinal: Annotated[int, Path(ge=1, le=4)],
    database: DatabaseSession,
    principal: Annotated[WatchPrincipal, Depends(require_watch_principal)],
) -> QuestionDetailResponse:
    queries = SessionQueries(SqlAlchemySessionQueryRepository(database))
    result = queries.get_question(principal.user_id, session_id, ordinal)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return QuestionDetailResponse.model_validate(result)


@router.get(
    "/{session_id}/questions/{ordinal}/steps/{step_ordinal}/render",
    operation_id="renderSolutionStep",
    responses={
        200: {"content": {"image/svg+xml": {}}, "description": "Rendered formula SVG"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Not found"},
    },
)
def render_solution_step(
    session_id: UUID,
    ordinal: Annotated[int, Path(ge=1, le=4)],
    step_ordinal: Annotated[int, Path(ge=1)],
    request: Request,
    database: DatabaseSession,
    principal: Annotated[WatchPrincipal, Depends(require_watch_principal)],
) -> Response:
    queries = SessionQueries(SqlAlchemySessionQueryRepository(database))
    result = queries.get_question(principal.user_id, session_id, ordinal)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    step = next((item for item in result.steps if item.ordinal == step_ordinal), None)
    if step is None or step.latex is None or step.render_url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Formula render not found",
        )
    asset_store: PrivateFormulaAssetStore = request.app.state.formula_asset_store
    renderer = FormulaRenderer(asset_store)
    rendered = renderer.render(
        latex=step.latex,
        fallback_text=step.plain_text,
        alt_text=step.alt_text or step.plain_text,
    )
    if not rendered.rendered or rendered.asset_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Formula render not found",
        )
    svg_bytes = asset_store.path_for(rendered.asset_key).read_bytes()
    return Response(
        content=svg_bytes,
        media_type="image/svg+xml",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "Cache-Control": "private, max-age=86400",
        },
    )

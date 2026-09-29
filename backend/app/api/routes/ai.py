from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingProvider, get_embedding_provider
from app.ai.ollama_client import LLMClient, get_llm_client
from app.api.deps import require_staff
from app.db.session import SessionFactory, get_db, get_session_factory
from app.models.user import User
from app.schemas.ai import (
    AIAnalysisRead,
    AIFeedbackCreate,
    AIFeedbackRead,
    AIResponseApprove,
    AIResponseEdit,
    AIResponseRead,
    AIResponseReject,
    AnalysisStartedResponse,
)
from app.services import ai_service, ticket_service

router = APIRouter(prefix="/tickets/{ticket_id}", tags=["ai"])


def _start(
    ticket_id: int,
    user: User,
    db: Session,
    background_tasks: BackgroundTasks,
    session_factory: SessionFactory,
    llm: LLMClient,
    embedder: EmbeddingProvider,
    regenerate: bool,
) -> AnalysisStartedResponse:
    ticket = ticket_service.get_ticket_for_user(db, user, ticket_id)
    ai_service.start_analysis(db, user, ticket, llm, regenerate=regenerate)
    background_tasks.add_task(ai_service.run_analysis_job, session_factory, llm, embedder, ticket.id)
    return AnalysisStartedResponse(
        ticket_id=ticket.id,
        analysis_status=ticket.ai_analysis_status,
        message="AI analysis started. The draft will require human review before it is sent.",
    )


@router.post("/analyze", response_model=AnalysisStartedResponse, status_code=status.HTTP_202_ACCEPTED)
def analyze_ticket(
    ticket_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
    session_factory: SessionFactory = Depends(get_session_factory),
    llm: LLMClient = Depends(get_llm_client),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
) -> AnalysisStartedResponse:
    return _start(ticket_id, user, db, background_tasks, session_factory, llm, embedder, regenerate=False)


@router.get("/ai-analysis", response_model=AIAnalysisRead)
def get_ai_analysis(
    ticket_id: int, user: User = Depends(require_staff), db: Session = Depends(get_db)
) -> AIAnalysisRead:
    return ai_service.get_analysis(db, user, ticket_id)


@router.post(
    "/ai-response/regenerate", response_model=AnalysisStartedResponse, status_code=status.HTTP_202_ACCEPTED
)
def regenerate_ai_response(
    ticket_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
    session_factory: SessionFactory = Depends(get_session_factory),
    llm: LLMClient = Depends(get_llm_client),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
) -> AnalysisStartedResponse:
    return _start(ticket_id, user, db, background_tasks, session_factory, llm, embedder, regenerate=True)


@router.post("/ai-response/approve", response_model=AIResponseRead)
def approve_ai_response(
    ticket_id: int,
    payload: AIResponseApprove | None = None,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> AIResponseRead:
    response = ai_service.approve_ai_response(db, user, ticket_id, payload or AIResponseApprove())
    return AIResponseRead.model_validate(response)


@router.post("/ai-response/reject", response_model=AIResponseRead)
def reject_ai_response(
    ticket_id: int,
    payload: AIResponseReject | None = None,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> AIResponseRead:
    response = ai_service.reject_ai_response(db, user, ticket_id, payload or AIResponseReject())
    return AIResponseRead.model_validate(response)


@router.patch("/ai-response", response_model=AIResponseRead)
def edit_ai_response(
    ticket_id: int,
    payload: AIResponseEdit,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> AIResponseRead:
    response = ai_service.edit_ai_response(db, user, ticket_id, payload)
    return AIResponseRead.model_validate(response)


@router.post("/ai-feedback", response_model=AIFeedbackRead, status_code=status.HTTP_201_CREATED)
def submit_ai_feedback(
    ticket_id: int,
    payload: AIFeedbackCreate,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> AIFeedbackRead:
    return AIFeedbackRead.model_validate(ai_service.submit_feedback(db, user, ticket_id, payload))

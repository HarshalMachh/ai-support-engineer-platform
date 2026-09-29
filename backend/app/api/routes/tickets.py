from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingProvider, get_embedding_provider
from app.ai.ollama_client import LLMClient, get_llm_client
from app.api.deps import get_current_user, require_roles, require_staff
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.db.session import SessionFactory, get_db, get_session_factory
from app.models.enums import AIAnalysisStatus, UserRole
from app.models.user import User
from app.schemas.common import Page
from app.schemas.ticket import (
    MessageCreate,
    TicketAssignRequest,
    TicketCreate,
    TicketDetail,
    TicketFilters,
    TicketResolveRequest,
    TicketSummary,
    TicketUpdate,
)
from app.services import ai_service, ticket_service

logger = get_logger(__name__)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketDetail, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_roles(UserRole.CUSTOMER)),
    db: Session = Depends(get_db),
    session_factory: SessionFactory = Depends(get_session_factory),
    llm: LLMClient = Depends(get_llm_client),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
) -> TicketDetail:
    ticket = ticket_service.create_ticket(db, user, payload)

    if get_settings().AI_AUTO_ANALYZE:
        try:
            ai_service.start_analysis(db, None, ticket, llm, regenerate=False)
            background_tasks.add_task(ai_service.run_analysis_job, session_factory, llm, embedder, ticket.id)
        except AppError as exc:
            # Ticket creation must succeed even when the local AI is offline.
            ticket.ai_analysis_status = AIAnalysisStatus.FAILED
            ticket.ai_error = exc.message
            db.commit()
            logger.warning(
                "Automatic AI analysis skipped",
                extra={"operation": "ai.auto_analyze", "ticket_id": ticket.id, "success": False, "error": exc.message},
            )
    return ticket_service.to_ticket_detail(ticket, user)


@router.get("", response_model=Page[TicketSummary])
def list_tickets(
    filters: TicketFilters = Depends(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[TicketSummary]:
    tickets, total = ticket_service.list_tickets(db, user, filters)
    items = [TicketSummary.model_validate(t) for t in tickets]
    return Page[TicketSummary].build(items, total, filters.page, filters.page_size)


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(ticket_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TicketDetail:
    ticket = ticket_service.get_ticket_for_user(db, user, ticket_id, include_messages=True)
    return ticket_service.to_ticket_detail(ticket, user)


@router.patch("/{ticket_id}", response_model=TicketDetail)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketDetail:
    ticket = ticket_service.update_ticket(db, user, ticket_id, payload)
    return ticket_service.to_ticket_detail(ticket, user)


@router.post("/{ticket_id}/messages", response_model=TicketDetail, status_code=status.HTTP_201_CREATED)
def add_message(
    ticket_id: int,
    payload: MessageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketDetail:
    ticket = ticket_service.add_message(db, user, ticket_id, payload)
    return ticket_service.to_ticket_detail(ticket, user)


@router.post("/{ticket_id}/assign", response_model=TicketDetail)
def assign_ticket(
    ticket_id: int,
    payload: TicketAssignRequest | None = None,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> TicketDetail:
    agent_id = payload.agent_id if payload else None
    ticket = ticket_service.assign_ticket(db, user, ticket_id, agent_id)
    return ticket_service.to_ticket_detail(ticket, user)


@router.post("/{ticket_id}/resolve", response_model=TicketDetail)
def resolve_ticket(
    ticket_id: int,
    payload: TicketResolveRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
    session_factory: SessionFactory = Depends(get_session_factory),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
) -> TicketDetail:
    ticket = ticket_service.resolve_ticket(db, user, ticket_id, payload)
    background_tasks.add_task(ai_service.index_resolved_ticket, session_factory, embedder, ticket.id)
    return ticket_service.to_ticket_detail(ticket, user)

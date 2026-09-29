"""Orchestrates AI analysis runs and the human review (approve / edit / reject) of drafts.

Invariant: the only code path that turns AI output into a customer-visible message is
`approve_ai_response`, which requires an authenticated agent or admin.
"""

import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.embeddings import EmbeddingError, EmbeddingProvider
from app.ai.graph import WorkflowDependencies, run_support_workflow
from app.ai.ollama_client import LLMClient
from app.ai.retrieval import VectorSearchError, search_knowledge
from app.ai.similar_tickets import resolved_ticket_text, search_similar_tickets
from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, ServiceUnavailableError
from app.core.logging import get_logger
from app.db.session import SessionFactory
from app.models.ai import AIFeedback, AIResponse
from app.models.enums import (
    AIAnalysisStatus,
    AIResponseStatus,
    MessageType,
    TicketCategory,
    TicketEventType,
    TicketPriority,
    TicketStatus,
)
from app.models.ticket import Ticket, TicketEmbedding, TicketMessage
from app.models.user import User
from app.schemas.ai import (
    AIAnalysisRead,
    AIFeedbackCreate,
    AIProgressEvent,
    AIResponseApprove,
    AIResponseEdit,
    AIResponseRead,
    AIResponseReject,
)
from app.services.event_service import record_event
from app.services.progress_service import get_progress, publish_progress, reset_progress
from app.services.ticket_service import FINAL_STATUSES, get_ticket_for_user

logger = get_logger(__name__)

STALE_ANALYSIS_AFTER = timedelta(minutes=10)
ANALYSIS_STARTED_EVENT = "analysis_started"
ANALYSIS_FAILED_EVENT = "analysis_failed"


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _is_running(ticket: Ticket) -> bool:
    if ticket.ai_analysis_status != AIAnalysisStatus.RUNNING or ticket.ai_analysis_started_at is None:
        return False
    return datetime.now(timezone.utc) - _as_aware(ticket.ai_analysis_started_at) < STALE_ANALYSIS_AFTER


def start_analysis(db: Session, user: User | None, ticket: Ticket, llm: LLMClient, *, regenerate: bool) -> None:
    """Validate preconditions and mark the ticket as RUNNING. The caller schedules the job."""
    if _is_running(ticket):
        raise ConflictError("AI analysis is already running for this ticket")
    if not llm.is_available():
        raise ServiceUnavailableError(llm.unavailable_message(), code="ollama_unavailable")

    ticket.ai_analysis_status = AIAnalysisStatus.RUNNING
    ticket.ai_analysis_started_at = datetime.now(timezone.utc)
    ticket.ai_error = None
    record_event(
        db,
        ticket.id,
        TicketEventType.AI_ANALYSIS_STARTED,
        {"regenerate": regenerate, "by": user.id if user else None, "model": llm.model_name},
    )
    db.commit()
    reset_progress(ticket.id)
    publish_progress(ticket.id, ANALYSIS_STARTED_EVENT, "AI analysis started")


def run_analysis_job(
    session_factory: SessionFactory, llm: LLMClient, embedder: EmbeddingProvider, ticket_id: int
) -> None:
    """Background job: run the LangGraph workflow and persist a PENDING draft."""
    settings = get_settings()
    started = time.perf_counter()
    db = session_factory()
    try:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None:
            return

        def knowledge_search(embedding: list[float]):
            try:
                return search_knowledge(db, embedding, settings.RAG_TOP_K, settings.RETRIEVAL_MIN_SIMILARITY)
            except VectorSearchError:
                db.rollback()
                raise

        def similar_search(embedding: list[float]):
            try:
                return search_similar_tickets(
                    db,
                    embedding,
                    settings.SIMILAR_TICKETS_TOP_K,
                    exclude_ticket_id=ticket_id,
                    min_similarity=settings.RETRIEVAL_MIN_SIMILARITY,
                )
            except VectorSearchError:
                db.rollback()
                raise

        deps = WorkflowDependencies(
            llm=llm,
            embedder=embedder,
            search_knowledge=knowledge_search,
            search_similar_tickets=similar_search,
            on_progress=lambda event, message: publish_progress(ticket_id, event, message),
        )
        result = run_support_workflow(
            deps,
            {
                "ticket_id": ticket.id,
                "subject": ticket.subject,
                "description": ticket.description,
                "environment": ticket.environment,
            },
        )

        latency_ms = round((time.perf_counter() - started) * 1000)
        if result.get("error"):
            _mark_failed(db, ticket_id, result["error"])
            logger.warning(
                "AI analysis failed",
                extra={"operation": "ai.analyze", "ticket_id": ticket_id, "latency_ms": latency_ms,
                       "success": False, "error": result["error"]},
            )
            return

        _save_draft(db, ticket_id, result, llm.model_name)
        logger.info(
            "AI analysis completed",
            extra={"operation": "ai.analyze", "ticket_id": ticket_id, "latency_ms": latency_ms, "success": True},
        )
    except Exception as exc:  # noqa: BLE001 - background jobs must never crash the worker
        db.rollback()
        logger.exception(
            "Unexpected AI analysis error",
            extra={"operation": "ai.analyze", "ticket_id": ticket_id, "success": False, "error": str(exc)},
        )
        _mark_failed(db, ticket_id, "Unexpected error during AI analysis. Check backend logs and try again.")
    finally:
        db.close()


def _mark_failed(db: Session, ticket_id: int, error: str) -> None:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        return
    ticket.ai_analysis_status = AIAnalysisStatus.FAILED
    ticket.ai_error = error
    record_event(db, ticket_id, TicketEventType.AI_ANALYSIS_FAILED, {"error": error[:500]})
    db.commit()
    publish_progress(ticket_id, ANALYSIS_FAILED_EVENT, error)


def _save_draft(db: Session, ticket_id: int, result: dict, model_name: str) -> AIResponse:
    ticket = db.get(Ticket, ticket_id)
    assert ticket is not None

    for previous in db.scalars(
        select(AIResponse).where(AIResponse.ticket_id == ticket_id, AIResponse.status == AIResponseStatus.PENDING)
    ):
        previous.status = AIResponseStatus.SUPERSEDED

    category = TicketCategory(result["category"])
    priority = TicketPriority(result["priority"])
    response = AIResponse(
        ticket_id=ticket_id,
        generated_response=result["draft_response"],
        reasoning_summary=result.get("reasoning_summary", ""),
        confidence_score=float(result.get("response_confidence", 0.0)),
        status=AIResponseStatus.PENDING,
        category=category,
        classification_confidence=result.get("classification_confidence"),
        priority=priority,
        priority_reason=result.get("priority_reason"),
        requires_more_information=bool(result.get("requires_more_information")),
        requested_information=result.get("requested_information", []),
        source_references=result.get("source_references", []),
        knowledge_results=result.get("knowledge_results", []),
        similar_tickets=result.get("similar_tickets", []),
        warnings=result.get("warnings", []),
        model_name=model_name,
    )
    db.add(response)
    db.flush()

    # AI suggestions fill empty fields only, so manual agent triage is never overwritten.
    if ticket.category is None:
        ticket.category = category
    if ticket.priority is None:
        ticket.priority = priority
    ticket.ai_confidence = result.get("classification_confidence")
    ticket.ai_analysis_status = AIAnalysisStatus.COMPLETED
    ticket.ai_error = None

    db.add(
        TicketMessage(
            ticket_id=ticket_id,
            sender_id=None,
            message=response.generated_response,
            message_type=MessageType.AI_DRAFT,
            ai_response_id=response.id,
        )
    )
    record_event(
        db,
        ticket_id,
        TicketEventType.AI_ANALYSIS_COMPLETED,
        {"ai_response_id": response.id, "category": category.value, "priority": priority.value,
         "confidence": response.confidence_score},
    )
    db.commit()
    return response


def _latest_response(db: Session, ticket_id: int) -> AIResponse | None:
    return db.scalar(
        select(AIResponse)
        .options(selectinload(AIResponse.approver))
        .where(AIResponse.ticket_id == ticket_id)
        .order_by(AIResponse.created_at.desc(), AIResponse.id.desc())
        .limit(1)
    )


def _pending_response(db: Session, ticket_id: int) -> AIResponse:
    response = _latest_response(db, ticket_id)
    if response is None:
        raise NotFoundError("No AI response exists for this ticket. Run the AI analysis first.")
    if response.status != AIResponseStatus.PENDING:
        raise ConflictError(f"The latest AI response is already {response.status.value.lower()}")
    return response


def get_analysis(db: Session, user: User, ticket_id: int) -> AIAnalysisRead:
    ticket = get_ticket_for_user(db, user, ticket_id)
    latest = _latest_response(db, ticket_id)
    return AIAnalysisRead(
        ticket_id=ticket.id,
        analysis_status=ticket.ai_analysis_status,
        error=ticket.ai_error,
        progress=[AIProgressEvent(**event) for event in get_progress(ticket.id)],
        latest_response=AIResponseRead.model_validate(latest) if latest else None,
    )


def edit_ai_response(db: Session, user: User, ticket_id: int, payload: AIResponseEdit) -> AIResponse:
    get_ticket_for_user(db, user, ticket_id)
    response = _pending_response(db, ticket_id)
    response.edited_response = payload.edited_response.strip()
    record_event(db, ticket_id, TicketEventType.AI_RESPONSE_EDITED, {"ai_response_id": response.id, "by": user.id})
    db.commit()
    return response


def approve_ai_response(db: Session, user: User, ticket_id: int, payload: AIResponseApprove) -> AIResponse:
    """Human approval: the only way an AI draft reaches the customer conversation."""
    ticket = get_ticket_for_user(db, user, ticket_id)
    if ticket.status == TicketStatus.CLOSED:
        raise ConflictError("Cannot send a response on a closed ticket")
    response = _pending_response(db, ticket_id)

    final_text = (payload.edited_response or response.edited_response or response.generated_response).strip()
    if not final_text:
        raise ConflictError("The response text is empty")
    was_edited = final_text != response.generated_response.strip()

    response.status = AIResponseStatus.EDITED if was_edited else AIResponseStatus.APPROVED
    response.edited_response = final_text if was_edited else None
    response.approver = user

    db.add(
        TicketMessage(
            ticket_id=ticket_id,
            sender_id=user.id,
            message=final_text,
            message_type=MessageType.AGENT,
            ai_response_id=response.id,
        )
    )
    if ticket.assigned_agent_id is None:
        ticket.assigned_agent_id = user.id
    if ticket.status not in FINAL_STATUSES:
        ticket.status = TicketStatus.WAITING_FOR_CUSTOMER
    record_event(
        db,
        ticket_id,
        TicketEventType.AI_RESPONSE_APPROVED,
        {"ai_response_id": response.id, "edited": was_edited, "by": user.id},
    )
    db.commit()
    logger.info(
        "AI response approved",
        extra={"operation": "ai.approve", "ticket_id": ticket_id, "success": True},
    )
    return response


def reject_ai_response(db: Session, user: User, ticket_id: int, payload: AIResponseReject) -> AIResponse:
    get_ticket_for_user(db, user, ticket_id)
    response = _pending_response(db, ticket_id)
    response.status = AIResponseStatus.REJECTED
    response.rejection_reason = payload.reason
    record_event(
        db,
        ticket_id,
        TicketEventType.AI_RESPONSE_REJECTED,
        {"ai_response_id": response.id, "reason": payload.reason, "by": user.id},
    )
    db.commit()
    return response


def submit_feedback(db: Session, user: User, ticket_id: int, payload: AIFeedbackCreate) -> AIFeedback:
    get_ticket_for_user(db, user, ticket_id)
    if payload.ai_response_id is not None:
        response = db.get(AIResponse, payload.ai_response_id)
        if response is None or response.ticket_id != ticket_id:
            raise NotFoundError("AI response not found for this ticket")
    else:
        response = _latest_response(db, ticket_id)
        if response is None:
            raise NotFoundError("No AI response exists for this ticket")

    feedback = AIFeedback(ai_response_id=response.id, agent_id=user.id, rating=payload.rating, comments=payload.comments)
    db.add(feedback)
    record_event(
        db, ticket_id, TicketEventType.AI_FEEDBACK_SUBMITTED, {"ai_response_id": response.id, "rating": payload.rating}
    )
    db.commit()
    db.refresh(feedback)
    return feedback


def index_resolved_ticket(session_factory: SessionFactory, embedder: EmbeddingProvider, ticket_id: int) -> None:
    """Background job: embed a resolved ticket so future tickets can find it."""
    db = session_factory()
    try:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None or not ticket.resolution_summary:
            return
        text = resolved_ticket_text(ticket.subject, ticket.description, ticket.resolution_summary)
        vector = embedder.embed([text])[0]
        existing = db.scalar(select(TicketEmbedding).where(TicketEmbedding.ticket_id == ticket_id))
        if existing:
            existing.embedding = vector
            existing.resolution_summary = ticket.resolution_summary
        else:
            db.add(TicketEmbedding(ticket_id=ticket_id, embedding=vector, resolution_summary=ticket.resolution_summary))
        db.commit()
        logger.info("Resolved ticket indexed", extra={"operation": "ticket.index", "ticket_id": ticket_id, "success": True})
    except EmbeddingError as exc:
        db.rollback()
        logger.warning(
            "Could not embed resolved ticket",
            extra={"operation": "ticket.index", "ticket_id": ticket_id, "success": False, "error": str(exc)},
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception(
            "Unexpected error indexing ticket",
            extra={"operation": "ticket.index", "ticket_id": ticket_id, "success": False, "error": str(exc)},
        )
    finally:
        db.close()

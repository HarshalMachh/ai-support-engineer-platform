"""Real metrics computed from the database with aggregate queries (no fake data)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai import AIFeedback, AIResponse
from app.models.enums import AIResponseStatus, TicketCategory, TicketPriority, TicketStatus
from app.models.ticket import Ticket
from app.schemas.analytics import AIAnalytics, TicketAnalytics


def _grouped_counts(db: Session, column) -> dict[str, int]:
    rows = db.execute(select(column, func.count()).group_by(column)).all()
    return {(key.value if key is not None else "UNSET"): count for key, count in rows}


def ticket_analytics(db: Session) -> TicketAnalytics:
    by_status = _grouped_counts(db, Ticket.status)
    by_priority = _grouped_counts(db, Ticket.priority)
    by_category = _grouped_counts(db, Ticket.category)

    status_counts = {status.value: by_status.get(status.value, 0) for status in TicketStatus}
    priority_counts = {p.value: by_priority.get(p.value, 0) for p in TicketPriority}
    if by_priority.get("UNSET"):
        priority_counts["UNSET"] = by_priority["UNSET"]
    category_counts = {c.value: by_category.get(c.value, 0) for c in TicketCategory}
    if by_category.get("UNSET"):
        category_counts["UNSET"] = by_category["UNSET"]

    critical_open = db.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(Ticket.priority == TicketPriority.CRITICAL, Ticket.status.not_in((TicketStatus.RESOLVED, TicketStatus.CLOSED)))
    ) or 0
    unassigned = db.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(Ticket.assigned_agent_id.is_(None), Ticket.status.not_in((TicketStatus.RESOLVED, TicketStatus.CLOSED)))
    ) or 0

    return TicketAnalytics(
        total_tickets=sum(status_counts.values()),
        open_tickets=status_counts[TicketStatus.OPEN.value],
        in_progress_tickets=status_counts[TicketStatus.IN_PROGRESS.value],
        waiting_for_customer_tickets=status_counts[TicketStatus.WAITING_FOR_CUSTOMER.value],
        critical_tickets=critical_open,
        resolved_tickets=status_counts[TicketStatus.RESOLVED.value],
        closed_tickets=status_counts[TicketStatus.CLOSED.value],
        unassigned_tickets=unassigned,
        tickets_by_category=category_counts,
        tickets_by_priority=priority_counts,
        tickets_by_status=status_counts,
        average_resolution_time_hours=_average_resolution_hours(db),
    )


def _average_resolution_hours(db: Session) -> float | None:
    """Computed in Python so it works identically on PostgreSQL and SQLite."""
    rows = db.execute(
        select(Ticket.created_at, Ticket.resolved_at).where(Ticket.resolved_at.is_not(None))
    ).all()
    durations = [(resolved - created).total_seconds() for created, resolved in rows if resolved and created]
    if not durations:
        return None
    return round(sum(durations) / len(durations) / 3600, 2)


def ai_analytics(db: Session) -> AIAnalytics:
    by_status = _grouped_counts(db, AIResponse.status)
    approved = by_status.get(AIResponseStatus.APPROVED.value, 0)
    edited = by_status.get(AIResponseStatus.EDITED.value, 0)
    rejected = by_status.get(AIResponseStatus.REJECTED.value, 0)
    reviewed = approved + edited + rejected

    average_confidence = db.scalar(select(func.avg(AIResponse.confidence_score)))
    feedback_count = db.scalar(select(func.count()).select_from(AIFeedback)) or 0
    average_rating = db.scalar(select(func.avg(AIFeedback.rating)))

    return AIAnalytics(
        total_responses=sum(by_status.values()),
        pending_count=by_status.get(AIResponseStatus.PENDING.value, 0),
        approved_count=approved,
        edited_count=edited,
        rejected_count=rejected,
        superseded_count=by_status.get(AIResponseStatus.SUPERSEDED.value, 0),
        # Approved without changes, out of all reviewed drafts.
        approval_rate=round(approved / reviewed, 4) if reviewed else None,
        # Approved as-is or after edits, out of all reviewed drafts.
        acceptance_rate=round((approved + edited) / reviewed, 4) if reviewed else None,
        average_confidence=round(float(average_confidence), 4) if average_confidence is not None else None,
        average_feedback_rating=round(float(average_rating), 2) if average_rating is not None else None,
        feedback_count=feedback_count,
    )

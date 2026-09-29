from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationFailedError
from app.core.logging import get_logger
from app.models.enums import MessageType, TicketEventType, TicketStatus, UserRole
from app.models.ticket import Ticket, TicketMessage
from app.models.user import User
from app.schemas.ticket import (
    MessageCreate,
    MessageRead,
    TicketCreate,
    TicketDetail,
    TicketFilters,
    TicketResolveRequest,
    TicketUpdate,
)
from app.services.event_service import record_event

logger = get_logger(__name__)

CUSTOMER_VISIBLE_MESSAGE_TYPES = {MessageType.CUSTOMER, MessageType.AGENT, MessageType.SYSTEM}
FINAL_STATUSES = {TicketStatus.RESOLVED, TicketStatus.CLOSED}


def is_staff(user: User) -> bool:
    return user.role in (UserRole.AGENT, UserRole.ADMIN)


def _ticket_query(include_messages: bool = False):
    options = [selectinload(Ticket.customer), selectinload(Ticket.assigned_agent)]
    if include_messages:
        options.append(selectinload(Ticket.messages).selectinload(TicketMessage.sender))
    return select(Ticket).options(*options)


def get_ticket_for_user(db: Session, user: User, ticket_id: int, include_messages: bool = False) -> Ticket:
    """Load a ticket the user may access. Customers get 404 for other customers' tickets."""
    stmt = _ticket_query(include_messages).where(Ticket.id == ticket_id)
    if include_messages:
        # Messages may have been added in this session without touching the relationship.
        stmt = stmt.execution_options(populate_existing=True)
    ticket = db.scalar(stmt)
    if ticket is None or (not is_staff(user) and ticket.customer_id != user.id):
        raise NotFoundError("Ticket not found")
    return ticket


def to_ticket_detail(ticket: Ticket, viewer: User) -> TicketDetail:
    messages = ticket.messages
    if not is_staff(viewer):
        messages = [m for m in messages if m.message_type in CUSTOMER_VISIBLE_MESSAGE_TYPES]
    detail = TicketDetail.model_validate(ticket, from_attributes=True)
    detail.messages = [MessageRead.model_validate(m) for m in messages]
    if not is_staff(viewer):
        detail.ai_error = None
    return detail


def create_ticket(db: Session, customer: User, payload: TicketCreate) -> Ticket:
    ticket = Ticket(
        customer_id=customer.id,
        subject=payload.subject,
        description=payload.description,
        environment=payload.environment,
    )
    db.add(ticket)
    db.flush()
    db.add(
        TicketMessage(
            ticket_id=ticket.id,
            sender_id=customer.id,
            message=payload.description,
            message_type=MessageType.CUSTOMER,
        )
    )
    record_event(db, ticket.id, TicketEventType.TICKET_CREATED, {"customer_id": customer.id})
    db.commit()
    logger.info("Ticket created", extra={"operation": "ticket.create", "ticket_id": ticket.id, "success": True})
    return get_ticket_for_user(db, customer, ticket.id, include_messages=True)


def list_tickets(db: Session, user: User, filters: TicketFilters) -> tuple[list[Ticket], int]:
    stmt = _ticket_query()
    if not is_staff(user):
        stmt = stmt.where(Ticket.customer_id == user.id)
    if filters.status:
        stmt = stmt.where(Ticket.status == filters.status)
    if filters.priority:
        stmt = stmt.where(Ticket.priority == filters.priority)
    if filters.category:
        stmt = stmt.where(Ticket.category == filters.category)
    if filters.assigned_agent and is_staff(user):
        stmt = _apply_assignee_filter(stmt, filters.assigned_agent, user)
    if filters.search and filters.search.strip():
        term = filters.search.strip()
        pattern = f"%{term.lower()}%"
        conditions = [func.lower(Ticket.subject).like(pattern), func.lower(Ticket.description).like(pattern)]
        if term.lstrip("#").isdigit():
            conditions.append(Ticket.id == int(term.lstrip("#")))
        stmt = stmt.where(or_(*conditions))

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    tickets = db.scalars(
        stmt.order_by(Ticket.created_at.desc(), Ticket.id.desc())
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
    ).all()
    return list(tickets), total


def _apply_assignee_filter(stmt, assigned_agent: str, user: User):
    value = assigned_agent.strip().lower()
    if value == "me":
        return stmt.where(Ticket.assigned_agent_id == user.id)
    if value == "unassigned":
        return stmt.where(Ticket.assigned_agent_id.is_(None))
    if value.isdigit():
        return stmt.where(Ticket.assigned_agent_id == int(value))
    raise ValidationFailedError("assigned_agent must be an agent id, 'me' or 'unassigned'")


def _get_staff_user(db: Session, user_id: int) -> User:
    agent = db.get(User, user_id)
    if agent is None or agent.role not in (UserRole.AGENT, UserRole.ADMIN) or not agent.is_active:
        raise ValidationFailedError("Tickets can only be assigned to active agents or admins")
    return agent


def _change_status(db: Session, ticket: Ticket, new_status: TicketStatus, actor: User) -> None:
    if ticket.status == new_status:
        return
    old_status = ticket.status
    ticket.status = new_status
    event = TicketEventType.TICKET_CLOSED if new_status == TicketStatus.CLOSED else TicketEventType.STATUS_CHANGED
    record_event(db, ticket.id, event, {"from": old_status.value, "to": new_status.value, "by": actor.id})


def update_ticket(db: Session, user: User, ticket_id: int, payload: TicketUpdate) -> Ticket:
    ticket = get_ticket_for_user(db, user, ticket_id)
    changes = payload.model_dump(exclude_unset=True)

    if not is_staff(user):
        if set(changes) != {"status"} or changes["status"] != TicketStatus.CLOSED:
            raise PermissionDeniedError("Customers can only close their own tickets")
        if ticket.status == TicketStatus.CLOSED:
            raise ConflictError("Ticket is already closed")
        _change_status(db, ticket, TicketStatus.CLOSED, user)
        db.commit()
        return get_ticket_for_user(db, user, ticket_id, include_messages=True)

    if changes.get("status") == TicketStatus.RESOLVED:
        raise ValidationFailedError("Use POST /api/tickets/{ticket_id}/resolve with a resolution summary")

    if "assigned_agent_id" in changes:
        agent_id = changes["assigned_agent_id"]
        if agent_id not in (None, user.id) and user.role != UserRole.ADMIN:
            raise PermissionDeniedError("Agents can only assign tickets to themselves")
        if agent_id is not None:
            _get_staff_user(db, agent_id)
        if agent_id != ticket.assigned_agent_id:
            ticket.assigned_agent_id = agent_id
            record_event(db, ticket.id, TicketEventType.AGENT_ASSIGNED, {"agent_id": agent_id, "by": user.id})

    for field in ("priority", "category"):
        if field in changes and changes[field] is not None and changes[field] != getattr(ticket, field):
            record_event(
                db,
                ticket.id,
                TicketEventType.TICKET_UPDATED,
                {"field": field, "from": getattr(getattr(ticket, field), "value", None), "to": changes[field].value},
            )
            setattr(ticket, field, changes[field])

    if changes.get("status") is not None:
        _change_status(db, ticket, changes["status"], user)

    db.commit()
    return get_ticket_for_user(db, user, ticket_id, include_messages=True)


def add_message(db: Session, user: User, ticket_id: int, payload: MessageCreate) -> Ticket:
    ticket = get_ticket_for_user(db, user, ticket_id)
    if ticket.status == TicketStatus.CLOSED:
        raise ConflictError("This ticket is closed. Please open a new ticket.")

    if is_staff(user):
        message_type = MessageType.AGENT
        if ticket.status not in FINAL_STATUSES:
            _change_status(db, ticket, TicketStatus.WAITING_FOR_CUSTOMER, user)
        if ticket.assigned_agent_id is None:
            ticket.assigned_agent_id = user.id
            record_event(db, ticket.id, TicketEventType.AGENT_ASSIGNED, {"agent_id": user.id, "by": user.id})
    else:
        message_type = MessageType.CUSTOMER
        if ticket.status == TicketStatus.RESOLVED:
            _change_status(db, ticket, TicketStatus.OPEN, user)
            ticket.resolved_at = None
            record_event(db, ticket.id, TicketEventType.TICKET_REOPENED, {"by": user.id})
        elif ticket.status == TicketStatus.WAITING_FOR_CUSTOMER:
            _change_status(db, ticket, TicketStatus.IN_PROGRESS, user)

    db.add(TicketMessage(ticket_id=ticket.id, sender_id=user.id, message=payload.message, message_type=message_type))
    ticket.updated_at = datetime.now(timezone.utc)
    record_event(db, ticket.id, TicketEventType.MESSAGE_ADDED, {"message_type": message_type.value, "by": user.id})
    db.commit()
    return get_ticket_for_user(db, user, ticket_id, include_messages=True)


def assign_ticket(db: Session, user: User, ticket_id: int, agent_id: int | None) -> Ticket:
    ticket = get_ticket_for_user(db, user, ticket_id)
    target_id = agent_id or user.id
    if target_id != user.id and user.role != UserRole.ADMIN:
        raise PermissionDeniedError("Agents can only assign tickets to themselves")
    _get_staff_user(db, target_id)

    if ticket.assigned_agent_id != target_id:
        ticket.assigned_agent_id = target_id
        record_event(db, ticket.id, TicketEventType.AGENT_ASSIGNED, {"agent_id": target_id, "by": user.id})
    if ticket.status == TicketStatus.OPEN:
        _change_status(db, ticket, TicketStatus.IN_PROGRESS, user)
    db.commit()
    return get_ticket_for_user(db, user, ticket_id, include_messages=True)


def resolve_ticket(db: Session, user: User, ticket_id: int, payload: TicketResolveRequest) -> Ticket:
    ticket = get_ticket_for_user(db, user, ticket_id)
    if ticket.status in FINAL_STATUSES:
        raise ConflictError(f"Ticket is already {ticket.status.value.lower()}")

    _change_status(db, ticket, TicketStatus.RESOLVED, user)
    ticket.resolution_summary = payload.resolution_summary
    ticket.resolved_at = datetime.now(timezone.utc)
    if ticket.assigned_agent_id is None:
        ticket.assigned_agent_id = user.id
    db.add(
        TicketMessage(
            ticket_id=ticket.id,
            sender_id=user.id,
            message=f"Ticket marked as resolved: {payload.resolution_summary}",
            message_type=MessageType.SYSTEM,
        )
    )
    record_event(db, ticket.id, TicketEventType.TICKET_RESOLVED, {"by": user.id})
    db.commit()
    logger.info("Ticket resolved", extra={"operation": "ticket.resolve", "ticket_id": ticket.id, "success": True})
    return get_ticket_for_user(db, user, ticket_id, include_messages=True)

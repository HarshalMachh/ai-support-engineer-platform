from typing import Any

from sqlalchemy.orm import Session

from app.models.enums import TicketEventType
from app.models.ticket import TicketEvent


def record_event(
    db: Session, ticket_id: int, event_type: TicketEventType, metadata: dict[str, Any] | None = None
) -> TicketEvent:
    """Add an audit event to the session; the caller owns the transaction."""
    event = TicketEvent(ticket_id=ticket_id, event_type=event_type, event_metadata=metadata or {})
    db.add(event)
    return event

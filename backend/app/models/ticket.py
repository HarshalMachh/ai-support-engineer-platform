from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, TimestampMixin
from app.db.types import JSONType, embedding_vector, string_enum
from app.models.enums import (
    AIAnalysisStatus,
    MessageType,
    TicketCategory,
    TicketEventType,
    TicketPriority,
    TicketStatus,
)

if TYPE_CHECKING:
    from app.models.ai import AIResponse
    from app.models.user import User


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_agent_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[str] = mapped_column(String(100), nullable=False, default="production")
    # Category and priority are set by the AI workflow (or an agent) after creation.
    category: Mapped[TicketCategory | None] = mapped_column(string_enum(TicketCategory))
    priority: Mapped[TicketPriority | None] = mapped_column(string_enum(TicketPriority))
    status: Mapped[TicketStatus] = mapped_column(
        string_enum(TicketStatus), nullable=False, default=TicketStatus.OPEN
    )
    ai_confidence: Mapped[float | None] = mapped_column(Float)
    ai_analysis_status: Mapped[AIAnalysisStatus] = mapped_column(
        string_enum(AIAnalysisStatus), nullable=False, default=AIAnalysisStatus.IDLE
    )
    ai_analysis_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_error: Mapped[str | None] = mapped_column(Text)
    resolution_summary: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped["User"] = relationship(back_populates="customer_tickets", foreign_keys=[customer_id])
    assigned_agent: Mapped["User | None"] = relationship(
        back_populates="assigned_tickets", foreign_keys=[assigned_agent_id]
    )
    messages: Mapped[list["TicketMessage"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", order_by="TicketMessage.created_at"
    )
    ai_responses: Mapped[list["AIResponse"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", order_by="AIResponse.created_at"
    )
    events: Mapped[list["TicketEvent"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", order_by="TicketEvent.created_at"
    )
    embedding: Mapped["TicketEmbedding | None"] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        Index("ix_tickets_customer_id", "customer_id"),
        Index("ix_tickets_assigned_agent_id", "assigned_agent_id"),
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_priority", "priority"),
        Index("ix_tickets_category", "category"),
        Index("ix_tickets_created_at", "created_at"),
    )


class TicketMessage(CreatedAtMixin, Base):
    __tablename__ = "ticket_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[MessageType] = mapped_column(string_enum(MessageType), nullable=False)
    # Set when an agent message originated from an approved/edited AI draft.
    ai_response_id: Mapped[int | None] = mapped_column(ForeignKey("ai_responses.id", ondelete="SET NULL"))

    ticket: Mapped[Ticket] = relationship(back_populates="messages")
    sender: Mapped["User | None"] = relationship()

    __table_args__ = (Index("ix_ticket_messages_ticket_id_created_at", "ticket_id", "created_at"),)


class TicketEmbedding(CreatedAtMixin, Base):
    __tablename__ = "ticket_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    embedding: Mapped[Any] = mapped_column(embedding_vector(), nullable=False)
    resolution_summary: Mapped[str] = mapped_column(Text, nullable=False)

    ticket: Mapped[Ticket] = relationship(back_populates="embedding")


class TicketEvent(CreatedAtMixin, Base):
    __tablename__ = "ticket_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[TicketEventType] = mapped_column(string_enum(TicketEventType, 48), nullable=False)
    # "metadata" is reserved by SQLAlchemy's declarative API, so the attribute is renamed.
    event_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONType, nullable=False, default=dict)

    ticket: Mapped[Ticket] = relationship(back_populates="events")

    __table_args__ = (Index("ix_ticket_events_ticket_id_created_at", "ticket_id", "created_at"),)

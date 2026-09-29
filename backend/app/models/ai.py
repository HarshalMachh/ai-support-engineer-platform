from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, TimestampMixin
from app.db.types import JSONType, string_enum
from app.models.enums import AIResponseStatus, TicketCategory, TicketPriority

if TYPE_CHECKING:
    from app.models.ticket import Ticket
    from app.models.user import User


class AIResponse(TimestampMixin, Base):
    """One run of the AI workflow for a ticket, awaiting (or after) human review."""

    __tablename__ = "ai_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    generated_response: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[AIResponseStatus] = mapped_column(
        string_enum(AIResponseStatus), nullable=False, default=AIResponseStatus.PENDING
    )
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    edited_response: Mapped[str | None] = mapped_column(Text)

    # Analysis context captured at generation time so reviewers see exactly what the model saw.
    category: Mapped[TicketCategory | None] = mapped_column(string_enum(TicketCategory))
    classification_confidence: Mapped[float | None] = mapped_column(Float)
    priority: Mapped[TicketPriority | None] = mapped_column(string_enum(TicketPriority))
    priority_reason: Mapped[str | None] = mapped_column(Text)
    requires_more_information: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requested_information: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    source_references: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    knowledge_results: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, nullable=False, default=list)
    similar_tickets: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, nullable=False, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    ticket: Mapped["Ticket"] = relationship(back_populates="ai_responses")
    approver: Mapped["User | None"] = relationship(foreign_keys=[approved_by])
    feedback: Mapped[list["AIFeedback"]] = relationship(back_populates="ai_response", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_ai_responses_ticket_id_created_at", "ticket_id", "created_at"),
        Index("ix_ai_responses_status", "status"),
    )


class AIFeedback(CreatedAtMixin, Base):
    __tablename__ = "ai_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    ai_response_id: Mapped[int] = mapped_column(
        ForeignKey("ai_responses.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comments: Mapped[str | None] = mapped_column(Text)

    ai_response: Mapped[AIResponse] = relationship(back_populates="feedback")
    agent: Mapped["User | None"] = relationship()

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="rating_range"),
        Index("ix_ai_feedback_ai_response_id", "ai_response_id"),
    )

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AIAnalysisStatus,
    MessageType,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)
from app.schemas.common import ORMModel
from app.schemas.user import UserBrief


class StrippedModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class TicketCreate(StrippedModel):
    subject: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=10_000)
    environment: str = Field(default="production", min_length=2, max_length=100)


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    category: TicketCategory | None = None
    assigned_agent_id: int | None = None


class TicketAssignRequest(BaseModel):
    agent_id: int | None = Field(default=None, description="Defaults to the current agent")


class TicketResolveRequest(StrippedModel):
    resolution_summary: str = Field(min_length=5, max_length=5_000)


class MessageCreate(StrippedModel):
    message: str = Field(min_length=1, max_length=10_000)


class MessageRead(ORMModel):
    id: int
    ticket_id: int
    sender: UserBrief | None
    message: str
    message_type: MessageType
    ai_response_id: int | None
    created_at: datetime


class TicketSummary(ORMModel):
    id: int
    subject: str
    environment: str
    category: TicketCategory | None
    priority: TicketPriority | None
    status: TicketStatus
    ai_confidence: float | None
    ai_analysis_status: AIAnalysisStatus
    customer: UserBrief
    assigned_agent: UserBrief | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class TicketDetail(TicketSummary):
    description: str
    resolution_summary: str | None
    ai_error: str | None
    messages: list[MessageRead]


class TicketFilters(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    category: TicketCategory | None = None
    assigned_agent: str | None = Field(
        default=None, description="Agent id, 'me' for the current user, or 'unassigned'"
    )
    search: str | None = Field(default=None, max_length=200)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

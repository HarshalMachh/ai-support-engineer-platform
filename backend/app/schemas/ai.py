from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AIAnalysisStatus, AIResponseStatus, TicketCategory, TicketPriority
from app.schemas.common import ORMModel
from app.schemas.user import UserBrief


class KnowledgeResult(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    filename: str
    chunk_index: int
    content: str
    similarity: float


class SimilarTicket(BaseModel):
    ticket_id: int
    subject: str
    similarity: float
    resolution_summary: str


class AIProgressEvent(BaseModel):
    event: str
    message: str
    timestamp: datetime


class AIResponseRead(ORMModel):
    id: int
    ticket_id: int
    generated_response: str
    edited_response: str | None
    reasoning_summary: str
    confidence_score: float
    status: AIResponseStatus
    approver: UserBrief | None
    category: TicketCategory | None
    classification_confidence: float | None
    priority: TicketPriority | None
    priority_reason: str | None
    requires_more_information: bool
    requested_information: list[str]
    source_references: list[str]
    knowledge_results: list[KnowledgeResult]
    similar_tickets: list[SimilarTicket]
    warnings: list[str]
    model_name: str
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class AIAnalysisRead(BaseModel):
    ticket_id: int
    analysis_status: AIAnalysisStatus
    error: str | None
    progress: list[AIProgressEvent]
    latest_response: AIResponseRead | None


class AnalysisStartedResponse(BaseModel):
    ticket_id: int
    analysis_status: AIAnalysisStatus
    message: str


class AIResponseEdit(BaseModel):
    edited_response: str = Field(min_length=1, max_length=10_000)


class AIResponseApprove(BaseModel):
    edited_response: str | None = Field(
        default=None, max_length=10_000, description="Optional final edit applied while approving"
    )


class AIResponseReject(BaseModel):
    reason: str | None = Field(default=None, max_length=2_000)


class AIFeedbackCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comments: str | None = Field(default=None, max_length=2_000)
    ai_response_id: int | None = Field(default=None, description="Defaults to the latest AI response")


class AIFeedbackRead(ORMModel):
    id: int
    ai_response_id: int
    agent_id: int | None
    rating: int
    comments: str | None
    created_at: datetime

import operator
from typing import Annotated, Any, TypedDict


class SupportTicketState(TypedDict, total=False):
    """State passed between LangGraph nodes for one ticket analysis run."""

    ticket_id: int
    subject: str
    description: str
    environment: str

    category: str
    classification_confidence: float

    priority: str
    priority_reason: str
    priority_confidence: float

    knowledge_results: list[dict[str, Any]]
    similar_tickets: list[dict[str, Any]]

    draft_response: str
    reasoning_summary: str
    response_confidence: float
    requires_more_information: bool
    requested_information: list[str]
    source_references: list[str]

    awaiting_human_review: bool
    # Non-fatal problems (e.g. retrieval failed); nodes append, never overwrite.
    warnings: Annotated[list[str], operator.add]
    # Fatal problem; the graph routes straight to END when set.
    error: str | None

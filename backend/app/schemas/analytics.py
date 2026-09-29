from pydantic import BaseModel


class TicketAnalytics(BaseModel):
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    waiting_for_customer_tickets: int
    critical_tickets: int
    resolved_tickets: int
    closed_tickets: int
    unassigned_tickets: int
    tickets_by_category: dict[str, int]
    tickets_by_priority: dict[str, int]
    tickets_by_status: dict[str, int]
    average_resolution_time_hours: float | None


class AIAnalytics(BaseModel):
    total_responses: int
    pending_count: int
    approved_count: int
    edited_count: int
    rejected_count: int
    superseded_count: int
    approval_rate: float | None
    acceptance_rate: float | None
    average_confidence: float | None
    average_feedback_rating: float | None
    feedback_count: int

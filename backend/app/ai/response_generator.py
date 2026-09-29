from typing import Any

from pydantic import BaseModel, Field

from app.ai.ollama_client import LLMClient
from app.ai.prompts import RESPONSE_SYSTEM_PROMPT, response_prompt


class ResponseOutput(BaseModel):
    draft_response: str = Field(min_length=1)
    reasoning_summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    requires_more_information: bool
    requested_information: list[str] = Field(default_factory=list)
    source_references: list[str] = Field(default_factory=list)


def allowed_source_references(
    knowledge_results: list[dict[str, Any]], similar_tickets: list[dict[str, Any]]
) -> dict[str, str]:
    """Map normalised reference -> canonical label for every source actually retrieved."""
    allowed: dict[str, str] = {}
    for item in knowledge_results:
        for label in (item["document_title"], item["filename"]):
            allowed[label.strip().lower()] = item["document_title"]
    for item in similar_tickets:
        label = f"Ticket #{item['ticket_id']}"
        allowed[label.lower()] = label
        allowed[f"#{item['ticket_id']}"] = label
        allowed[str(item["ticket_id"])] = label
    return allowed


def filter_source_references(
    references: list[str], knowledge_results: list[dict[str, Any]], similar_tickets: list[dict[str, Any]]
) -> tuple[list[str], list[str]]:
    """Keep only references to retrieved sources. Returns (kept, dropped)."""
    allowed = allowed_source_references(knowledge_results, similar_tickets)
    kept: list[str] = []
    dropped: list[str] = []
    for reference in references:
        canonical = allowed.get(reference.strip().removeprefix("[Source: ").rstrip("]").strip().lower())
        if canonical is None:
            dropped.append(reference)
        elif canonical not in kept:
            kept.append(canonical)
    return kept, dropped


def generate_response(
    llm: LLMClient,
    *,
    subject: str,
    description: str,
    environment: str,
    category: str,
    priority: str,
    knowledge_results: list[dict[str, Any]],
    similar_tickets: list[dict[str, Any]],
) -> ResponseOutput:
    prompt = response_prompt(
        subject, description, environment, category, priority, knowledge_results, similar_tickets
    )
    return llm.generate_structured(RESPONSE_SYSTEM_PROMPT, prompt, ResponseOutput)

from pydantic import BaseModel, Field

from app.ai.ollama_client import LLMClient
from app.ai.prompts import PRIORITY_SYSTEM_PROMPT, priority_prompt
from app.models.enums import TicketPriority


class PriorityOutput(BaseModel):
    priority: TicketPriority
    reason: str = Field(max_length=1_000)
    confidence: float = Field(ge=0.0, le=1.0)


def determine_priority(
    llm: LLMClient, subject: str, description: str, environment: str, category: str
) -> PriorityOutput:
    return llm.generate_structured(
        PRIORITY_SYSTEM_PROMPT,
        priority_prompt(subject, description, environment, category),
        PriorityOutput,
    )

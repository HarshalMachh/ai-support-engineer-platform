from pydantic import BaseModel, Field

from app.ai.ollama_client import LLMClient
from app.ai.prompts import CLASSIFIER_SYSTEM_PROMPT, classification_prompt
from app.models.enums import TicketCategory


class ClassificationOutput(BaseModel):
    category: TicketCategory
    confidence: float = Field(ge=0.0, le=1.0)


def classify_ticket(llm: LLMClient, subject: str, description: str) -> ClassificationOutput:
    return llm.generate_structured(
        CLASSIFIER_SYSTEM_PROMPT, classification_prompt(subject, description), ClassificationOutput
    )

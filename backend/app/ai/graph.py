"""LangGraph workflow for AI-assisted ticket analysis.

START -> classify_ticket -> determine_priority -> retrieve_knowledge
      -> retrieve_similar_tickets -> generate_response -> human_review_pause -> END

The graph never sends anything to the customer. It ends at `human_review_pause`, which marks
the draft as awaiting review; approval happens later through the API by a human agent.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.ai.classifier import classify_ticket
from app.ai.embeddings import EmbeddingError, EmbeddingProvider
from app.ai.ollama_client import LLMClient, MalformedAIOutputError, OllamaUnavailableError
from app.ai.priority import determine_priority
from app.ai.response_generator import filter_source_references, generate_response
from app.ai.retrieval import VectorSearchError, ticket_query_text
from app.ai.state import SupportTicketState
from app.models.enums import TicketCategory, TicketPriority

DEFAULT_REQUESTED_INFORMATION = [
    "Relevant logs or error messages",
    "HTTP status code and API endpoint (if applicable)",
    "Timestamp of when the issue occurred (with timezone)",
    "Browser / client version and environment",
    "Any recent deployment or configuration change",
]
NO_CONTEXT_CONFIDENCE_CAP = 0.5


class ProgressEvent:
    CLASSIFICATION_STARTED = "classification_started"
    CLASSIFICATION_COMPLETED = "classification_completed"
    PRIORITY_COMPLETED = "priority_completed"
    RETRIEVAL_COMPLETED = "retrieval_completed"
    SIMILAR_TICKET_SEARCH_COMPLETED = "similar_ticket_search_completed"
    RESPONSE_GENERATED = "response_generated"


@dataclass
class WorkflowDependencies:
    llm: LLMClient
    embedder: EmbeddingProvider
    search_knowledge: Callable[[list[float]], list[dict[str, Any]]]
    search_similar_tickets: Callable[[list[float]], list[dict[str, Any]]]
    on_progress: Callable[[str, str], None] = lambda event, message: None
    _query_embedding: list[float] | None = field(default=None, init=False)

    def query_embedding(self, state: SupportTicketState) -> list[float]:
        if self._query_embedding is None:
            text = ticket_query_text(state["subject"], state["description"], state.get("environment"))
            self._query_embedding = self.embedder.embed([text])[0]
        return self._query_embedding


def build_support_graph(deps: WorkflowDependencies):
    def classify_node(state: SupportTicketState) -> dict[str, Any]:
        deps.on_progress(ProgressEvent.CLASSIFICATION_STARTED, "Classifying ticket")
        try:
            result = classify_ticket(deps.llm, state["subject"], state["description"])
            update: dict[str, Any] = {
                "category": result.category.value,
                "classification_confidence": result.confidence,
            }
        except OllamaUnavailableError as exc:
            return {"error": str(exc)}
        except MalformedAIOutputError:
            update = {
                "category": TicketCategory.OTHER.value,
                "classification_confidence": 0.0,
                "warnings": ["Classification output was malformed; defaulted to OTHER."],
            }
        deps.on_progress(
            ProgressEvent.CLASSIFICATION_COMPLETED,
            f"Category {update['category']} ({update['classification_confidence']:.0%} confidence)",
        )
        return update

    def priority_node(state: SupportTicketState) -> dict[str, Any]:
        try:
            result = determine_priority(
                deps.llm, state["subject"], state["description"], state.get("environment", ""), state["category"]
            )
            update: dict[str, Any] = {
                "priority": result.priority.value,
                "priority_reason": result.reason,
                "priority_confidence": result.confidence,
            }
        except OllamaUnavailableError as exc:
            return {"error": str(exc)}
        except MalformedAIOutputError:
            update = {
                "priority": TicketPriority.MEDIUM.value,
                "priority_reason": "Priority output was malformed; defaulted to MEDIUM for human review.",
                "priority_confidence": 0.0,
                "warnings": ["Priority output was malformed; defaulted to MEDIUM."],
            }
        deps.on_progress(ProgressEvent.PRIORITY_COMPLETED, f"Priority {update['priority']}")
        return update

    def retrieve_knowledge_node(state: SupportTicketState) -> dict[str, Any]:
        try:
            results = deps.search_knowledge(deps.query_embedding(state))
            update: dict[str, Any] = {"knowledge_results": results}
        except (EmbeddingError, VectorSearchError) as exc:
            update = {"knowledge_results": [], "warnings": [f"Knowledge retrieval failed: {exc}"]}
        deps.on_progress(
            ProgressEvent.RETRIEVAL_COMPLETED, f"Found {len(update['knowledge_results'])} knowledge chunks"
        )
        return update

    def retrieve_similar_node(state: SupportTicketState) -> dict[str, Any]:
        try:
            results = deps.search_similar_tickets(deps.query_embedding(state))
            update: dict[str, Any] = {"similar_tickets": results}
        except (EmbeddingError, VectorSearchError) as exc:
            update = {"similar_tickets": [], "warnings": [f"Similar ticket search failed: {exc}"]}
        deps.on_progress(
            ProgressEvent.SIMILAR_TICKET_SEARCH_COMPLETED,
            f"Found {len(update['similar_tickets'])} similar resolved tickets",
        )
        return update

    def generate_response_node(state: SupportTicketState) -> dict[str, Any]:
        knowledge = state.get("knowledge_results", [])
        similar = state.get("similar_tickets", [])
        try:
            result = generate_response(
                deps.llm,
                subject=state["subject"],
                description=state["description"],
                environment=state.get("environment", ""),
                category=state["category"],
                priority=state["priority"],
                knowledge_results=knowledge,
                similar_tickets=similar,
            )
        except OllamaUnavailableError as exc:
            return {"error": str(exc)}
        except MalformedAIOutputError as exc:
            return {"error": f"The AI model returned malformed output. Try regenerating. ({exc})"}

        warnings: list[str] = []
        sources, dropped = filter_source_references(result.source_references, knowledge, similar)
        if dropped:
            warnings.append(f"Removed source references not present in retrieved context: {', '.join(dropped)}")

        confidence = result.confidence
        if not knowledge and not similar:
            confidence = min(confidence, NO_CONTEXT_CONFIDENCE_CAP)
            warnings.append("No supporting documentation or similar tickets were found; verify carefully.")

        requested = [item for item in result.requested_information if item.strip()]
        if result.requires_more_information and not requested:
            requested = DEFAULT_REQUESTED_INFORMATION

        deps.on_progress(ProgressEvent.RESPONSE_GENERATED, "Draft response ready for human review")
        return {
            "draft_response": result.draft_response.strip(),
            "reasoning_summary": result.reasoning_summary.strip(),
            "response_confidence": confidence,
            "requires_more_information": result.requires_more_information,
            "requested_information": requested,
            "source_references": sources,
            "warnings": warnings,
        }

    def human_review_pause_node(state: SupportTicketState) -> dict[str, Any]:
        return {"awaiting_human_review": True}

    def stop_on_error(next_node: str) -> Callable[[SupportTicketState], str]:
        def route(state: SupportTicketState) -> str:
            return END if state.get("error") else next_node

        return route

    graph = StateGraph(SupportTicketState)
    graph.add_node("classify_ticket", classify_node)
    graph.add_node("determine_priority", priority_node)
    graph.add_node("retrieve_knowledge", retrieve_knowledge_node)
    graph.add_node("retrieve_similar_tickets", retrieve_similar_node)
    graph.add_node("generate_response", generate_response_node)
    graph.add_node("human_review_pause", human_review_pause_node)

    graph.add_edge(START, "classify_ticket")
    graph.add_conditional_edges("classify_ticket", stop_on_error("determine_priority"))
    graph.add_conditional_edges("determine_priority", stop_on_error("retrieve_knowledge"))
    graph.add_edge("retrieve_knowledge", "retrieve_similar_tickets")
    graph.add_edge("retrieve_similar_tickets", "generate_response")
    graph.add_conditional_edges("generate_response", stop_on_error("human_review_pause"))
    graph.add_edge("human_review_pause", END)
    return graph.compile()


def run_support_workflow(deps: WorkflowDependencies, initial_state: SupportTicketState) -> SupportTicketState:
    state: SupportTicketState = {"warnings": [], "error": None, **initial_state}
    return build_support_graph(deps).invoke(state)

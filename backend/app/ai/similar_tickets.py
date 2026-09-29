"""Similar resolved-ticket search using stored ticket embeddings."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import cosine_similarity
from app.ai.retrieval import VectorSearchError
from app.models.enums import TicketStatus
from app.models.ticket import Ticket, TicketEmbedding

SOLVED_STATUSES = (TicketStatus.RESOLVED, TicketStatus.CLOSED)


def resolved_ticket_text(subject: str, description: str, resolution: str) -> str:
    return f"{subject}\n{description}\nResolution: {resolution}"


def search_similar_tickets(
    db: Session,
    query_embedding: list[float],
    top_k: int,
    exclude_ticket_id: int | None = None,
    min_similarity: float = 0.0,
) -> list[dict[str, Any]]:
    try:
        if db.get_bind().dialect.name == "postgresql":
            rows = _search_postgres(db, query_embedding, top_k, exclude_ticket_id)
        else:
            rows = _search_in_python(db, query_embedding, top_k, exclude_ticket_id)
    except Exception as exc:  # noqa: BLE001
        raise VectorSearchError(f"Similar ticket search failed: {exc}") from exc

    return [
        {
            "ticket_id": ticket.id,
            "subject": ticket.subject,
            "similarity": round(similarity, 4),
            "resolution_summary": embedding.resolution_summary,
        }
        for embedding, ticket, similarity in rows
        if similarity >= min_similarity
    ]


def _base_query(exclude_ticket_id: int | None):
    stmt = (
        select(TicketEmbedding, Ticket)
        .join(Ticket, TicketEmbedding.ticket_id == Ticket.id)
        .where(Ticket.status.in_(SOLVED_STATUSES))
    )
    if exclude_ticket_id is not None:
        stmt = stmt.where(Ticket.id != exclude_ticket_id)
    return stmt


def _search_postgres(db: Session, query_embedding: list[float], top_k: int, exclude_ticket_id: int | None):
    distance = TicketEmbedding.embedding.cosine_distance(query_embedding).label("distance")
    stmt = _base_query(exclude_ticket_id).add_columns(distance).order_by(distance).limit(top_k)
    return [(emb, ticket, 1.0 - float(dist)) for emb, ticket, dist in db.execute(stmt).all()]


def _search_in_python(db: Session, query_embedding: list[float], top_k: int, exclude_ticket_id: int | None):
    scored = [
        (emb, ticket, cosine_similarity(list(emb.embedding), query_embedding))
        for emb, ticket in db.execute(_base_query(exclude_ticket_id)).all()
    ]
    scored.sort(key=lambda row: row[2], reverse=True)
    return scored[:top_k]

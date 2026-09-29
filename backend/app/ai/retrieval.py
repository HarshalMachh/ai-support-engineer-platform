"""Vector search over knowledge-base chunks (pgvector cosine distance)."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import cosine_similarity
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument


class VectorSearchError(Exception):
    """Vector search failed (database/pgvector problem)."""


def ticket_query_text(subject: str, description: str, environment: str | None) -> str:
    return f"{subject}\n{description}\nEnvironment: {environment or 'unknown'}"


def search_knowledge(
    db: Session, query_embedding: list[float], top_k: int, min_similarity: float = 0.0
) -> list[dict[str, Any]]:
    try:
        if db.get_bind().dialect.name == "postgresql":
            rows = _search_postgres(db, query_embedding, top_k)
        else:
            rows = _search_in_python(db, query_embedding, top_k)
    except Exception as exc:  # noqa: BLE001 - surfaced to callers as a typed error
        raise VectorSearchError(f"Knowledge vector search failed: {exc}") from exc

    return [
        {
            "chunk_id": chunk.id,
            "document_id": document.id,
            "document_title": document.title,
            "filename": document.filename,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "similarity": round(similarity, 4),
        }
        for chunk, document, similarity in rows
        if similarity >= min_similarity
    ]


def _search_postgres(
    db: Session, query_embedding: list[float], top_k: int
) -> list[tuple[KnowledgeChunk, KnowledgeDocument, float]]:
    distance = KnowledgeChunk.embedding.cosine_distance(query_embedding).label("distance")
    stmt = (
        select(KnowledgeChunk, KnowledgeDocument, distance)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .order_by(distance)
        .limit(top_k)
    )
    return [(chunk, document, 1.0 - float(dist)) for chunk, document, dist in db.execute(stmt).all()]


def _search_in_python(
    db: Session, query_embedding: list[float], top_k: int
) -> list[tuple[KnowledgeChunk, KnowledgeDocument, float]]:
    """Fallback for non-PostgreSQL databases (used by the SQLite test-suite)."""
    stmt = select(KnowledgeChunk, KnowledgeDocument).join(
        KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id
    )
    scored = [
        (chunk, document, cosine_similarity(list(chunk.embedding), query_embedding))
        for chunk, document in db.execute(stmt).all()
    ]
    scored.sort(key=lambda row: row[2], reverse=True)
    return scored[:top_k]

"""Knowledge base ingestion: upload -> extract -> clean -> chunk -> embed -> store in pgvector."""

import re
from pathlib import PurePath

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingError, EmbeddingProvider
from app.ai.retrieval import VectorSearchError, search_knowledge
from app.ai.text_processing import clean_text, extract_title, split_into_chunks
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ServiceUnavailableError, ValidationFailedError
from app.core.logging import get_logger
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.schemas.ai import KnowledgeResult
from app.schemas.knowledge import KnowledgeChunkRead, KnowledgeDocumentDetail, KnowledgeDocumentRead

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {".txt": "text/plain", ".md": "text/markdown"}
ALLOWED_UPLOAD_CONTENT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "application/octet-stream",
    "",
}
SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")
EMBED_BATCH_SIZE = 16


def sanitize_filename(filename: str | None) -> str:
    name = PurePath((filename or "").replace("\\", "/")).name
    name = SAFE_FILENAME.sub("_", name).strip("._")
    if not name:
        raise ValidationFailedError("A filename is required")
    return name[:200]


def validate_upload(filename: str | None, content_type: str | None, data: bytes) -> tuple[str, str, str]:
    """Return (safe_filename, canonical_content_type, decoded_text) or raise a validation error."""
    safe_name = sanitize_filename(filename)
    extension = PurePath(safe_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationFailedError("Only .txt and .md files are supported")
    if (content_type or "").split(";")[0].strip().lower() not in ALLOWED_UPLOAD_CONTENT_TYPES:
        raise ValidationFailedError(f"Unsupported content type '{content_type}'")
    max_bytes = get_settings().MAX_UPLOAD_BYTES
    if len(data) > max_bytes:
        raise ValidationFailedError(f"File is too large (max {max_bytes // 1000} KB)")
    if b"\x00" in data:
        raise ValidationFailedError("Binary files are not supported")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationFailedError("File must be UTF-8 encoded text") from exc
    return safe_name, ALLOWED_EXTENSIONS[extension], text


def ingest_document(
    db: Session, embedder: EmbeddingProvider, filename: str, content_type: str, raw_text: str
) -> KnowledgeDocument:
    settings = get_settings()
    text = clean_text(raw_text)
    if len(text) < 20:
        raise ValidationFailedError("Document does not contain enough text to index")

    chunks = split_into_chunks(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    try:
        vectors: list[list[float]] = []
        for start in range(0, len(chunks), EMBED_BATCH_SIZE):
            vectors.extend(embedder.embed(chunks[start : start + EMBED_BATCH_SIZE]))
    except EmbeddingError as exc:
        raise ServiceUnavailableError(str(exc), code="embedding_failed") from exc

    document = KnowledgeDocument(
        title=extract_title(text, PurePath(filename).stem.replace("_", " ").title()),
        filename=filename,
        content_type=content_type,
        content=text,
        size_bytes=len(raw_text.encode("utf-8")),
        embedding_model=embedder.model_name,
    )
    document.chunks = [
        KnowledgeChunk(chunk_index=index, content=chunk, embedding=vector)
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
    ]
    db.add(document)
    db.commit()
    db.refresh(document)
    logger.info(
        "Knowledge document ingested",
        extra={"operation": "knowledge.ingest", "success": True, "context": {"chunks": len(chunks)}},
    )
    return document


def _chunk_counts(db: Session, document_ids: list[int]) -> dict[int, int]:
    if not document_ids:
        return {}
    rows = db.execute(
        select(KnowledgeChunk.document_id, func.count(KnowledgeChunk.id))
        .where(KnowledgeChunk.document_id.in_(document_ids))
        .group_by(KnowledgeChunk.document_id)
    ).all()
    return {document_id: count for document_id, count in rows}


def to_document_read(document: KnowledgeDocument, chunk_count: int) -> KnowledgeDocumentRead:
    return KnowledgeDocumentRead(
        id=document.id,
        title=document.title,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        embedding_model=document.embedding_model,
        chunk_count=chunk_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def list_documents(db: Session) -> list[KnowledgeDocumentRead]:
    documents = list(db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.title)).all())
    counts = _chunk_counts(db, [d.id for d in documents])
    return [to_document_read(d, counts.get(d.id, 0)) for d in documents]


def get_document(db: Session, document_id: int) -> KnowledgeDocumentDetail:
    document = db.get(KnowledgeDocument, document_id)
    if document is None:
        raise NotFoundError("Document not found")
    base = to_document_read(document, len(document.chunks))
    return KnowledgeDocumentDetail(
        **base.model_dump(),
        content=document.content,
        chunks=[KnowledgeChunkRead.model_validate(chunk) for chunk in document.chunks],
    )


def delete_document(db: Session, document_id: int) -> None:
    document = db.get(KnowledgeDocument, document_id)
    if document is None:
        raise NotFoundError("Document not found")
    db.delete(document)
    db.commit()


def search(db: Session, embedder: EmbeddingProvider, query: str, top_k: int) -> list[KnowledgeResult]:
    try:
        vector = embedder.embed([query])[0]
    except EmbeddingError as exc:
        raise ServiceUnavailableError(str(exc), code="embedding_failed") from exc
    try:
        results = search_knowledge(db, vector, top_k)
    except VectorSearchError as exc:
        db.rollback()
        raise ServiceUnavailableError("Vector search failed. Is the pgvector extension installed?",
                                      code="vector_search_failed") from exc
    return [KnowledgeResult(**result) for result in results]

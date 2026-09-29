from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingProvider, get_embedding_provider
from app.api.deps import require_admin, require_staff
from app.core.config import get_settings
from app.core.exceptions import ValidationFailedError
from app.db.session import get_db
from app.schemas.knowledge import (
    KnowledgeDocumentDetail,
    KnowledgeDocumentRead,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services import knowledge_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post(
    "/documents",
    response_model=KnowledgeDocumentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
) -> KnowledgeDocumentRead:
    # Read one byte past the limit so oversized files are rejected without loading them fully.
    data = await file.read(get_settings().MAX_UPLOAD_BYTES + 1)
    if not data:
        raise ValidationFailedError("Uploaded file is empty")
    filename, content_type, text = knowledge_service.validate_upload(file.filename, file.content_type, data)
    document = knowledge_service.ingest_document(db, embedder, filename, content_type, text)
    return knowledge_service.to_document_read(document, len(document.chunks))


@router.get("/documents", response_model=list[KnowledgeDocumentRead], dependencies=[Depends(require_staff)])
def list_documents(db: Session = Depends(get_db)) -> list[KnowledgeDocumentRead]:
    return knowledge_service.list_documents(db)


@router.get(
    "/documents/{document_id}", response_model=KnowledgeDocumentDetail, dependencies=[Depends(require_staff)]
)
def get_document(document_id: int, db: Session = Depends(get_db)) -> KnowledgeDocumentDetail:
    return knowledge_service.get_document(db, document_id)


@router.delete(
    "/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)]
)
def delete_document(document_id: int, db: Session = Depends(get_db)) -> None:
    knowledge_service.delete_document(db, document_id)


@router.post("/search", response_model=KnowledgeSearchResponse, dependencies=[Depends(require_staff)])
def search_knowledge(
    payload: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
    embedder: EmbeddingProvider = Depends(get_embedding_provider),
) -> KnowledgeSearchResponse:
    results = knowledge_service.search(db, embedder, payload.query, payload.top_k)
    return KnowledgeSearchResponse(query=payload.query, results=results)

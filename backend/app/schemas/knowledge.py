from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.ai import KnowledgeResult
from app.schemas.common import ORMModel


class KnowledgeDocumentRead(ORMModel):
    id: int
    title: str
    filename: str
    content_type: str
    size_bytes: int
    embedding_model: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class KnowledgeChunkRead(ORMModel):
    id: int
    chunk_index: int
    content: str


class KnowledgeDocumentDetail(KnowledgeDocumentRead):
    content: str
    chunks: list[KnowledgeChunkRead]


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2_000)
    top_k: int = Field(default=5, ge=1, le=20)


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeResult]

from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, TimestampMixin
from app.db.types import embedding_vector


class KnowledgeDocument(TimestampMixin, Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding_model: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="KnowledgeChunk.chunk_index"
    )

    __table_args__ = (Index("ix_knowledge_documents_filename", "filename"),)


class KnowledgeChunk(CreatedAtMixin, Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any] = mapped_column(embedding_vector(), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")

    __table_args__ = (Index("ix_knowledge_chunks_document_id_chunk_index", "document_id", "chunk_index", unique=True),)

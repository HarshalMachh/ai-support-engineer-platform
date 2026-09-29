"""Initial schema: users, tickets, messages, AI responses, knowledge base, embeddings.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from app.core.config import get_settings

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIMENSION = get_settings().EMBEDDING_DIMENSION


def timestamps(include_updated: bool = True) -> list[sa.Column]:
    columns = [sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())]
    if include_updated:
        columns.append(
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
        )
    return columns


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "customer_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_tickets_customer_id_users"),
            nullable=False,
        ),
        sa.Column(
            "assigned_agent_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_tickets_assigned_agent_id_users"),
            nullable=True,
        ),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("environment", sa.String(100), nullable=False, server_default="production"),
        sa.Column("category", sa.String(32), nullable=True),
        sa.Column("priority", sa.String(32), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("ai_analysis_status", sa.String(32), nullable=False, server_default="IDLE"),
        sa.Column("ai_analysis_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_error", sa.Text(), nullable=True),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
    )
    op.create_index("ix_tickets_customer_id", "tickets", ["customer_id"])
    op.create_index("ix_tickets_assigned_agent_id", "tickets", ["assigned_agent_id"])
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_priority", "tickets", ["priority"])
    op.create_index("ix_tickets_category", "tickets", ["category"])
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"])

    op.create_table(
        "ai_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE", name="fk_ai_responses_ticket_id_tickets"),
            nullable=False,
        ),
        sa.Column("generated_response", sa.Text(), nullable=False),
        sa.Column("reasoning_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column(
            "approved_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_ai_responses_approved_by_users"),
            nullable=True,
        ),
        sa.Column("edited_response", sa.Text(), nullable=True),
        sa.Column("category", sa.String(32), nullable=True),
        sa.Column("classification_confidence", sa.Float(), nullable=True),
        sa.Column("priority", sa.String(32), nullable=True),
        sa.Column("priority_reason", sa.Text(), nullable=True),
        sa.Column("requires_more_information", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requested_information", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("source_references", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("knowledge_results", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("similar_tickets", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("warnings", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("model_name", sa.String(120), nullable=False, server_default=""),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        *timestamps(),
    )
    op.create_index("ix_ai_responses_ticket_id_created_at", "ai_responses", ["ticket_id", "created_at"])
    op.create_index("ix_ai_responses_status", "ai_responses", ["status"])

    op.create_table(
        "ai_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ai_response_id",
            sa.Integer(),
            sa.ForeignKey("ai_responses.id", ondelete="CASCADE", name="fk_ai_feedback_ai_response_id_ai_responses"),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_ai_feedback_agent_id_users"),
            nullable=True,
        ),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        *timestamps(include_updated=False),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_ai_feedback_rating_range"),
    )
    op.create_index("ix_ai_feedback_ai_response_id", "ai_feedback", ["ai_response_id"])

    op.create_table(
        "ticket_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE", name="fk_ticket_messages_ticket_id_tickets"),
            nullable=False,
        ),
        sa.Column(
            "sender_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_ticket_messages_sender_id_users"),
            nullable=True,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(32), nullable=False),
        sa.Column(
            "ai_response_id",
            sa.Integer(),
            sa.ForeignKey(
                "ai_responses.id", ondelete="SET NULL", name="fk_ticket_messages_ai_response_id_ai_responses"
            ),
            nullable=True,
        ),
        *timestamps(include_updated=False),
    )
    op.create_index("ix_ticket_messages_ticket_id_created_at", "ticket_messages", ["ticket_id", "created_at"])

    op.create_table(
        "ticket_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE", name="fk_ticket_events_ticket_id_tickets"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(48), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        *timestamps(include_updated=False),
    )
    op.create_index("ix_ticket_events_ticket_id_created_at", "ticket_events", ["ticket_id", "created_at"])

    op.create_table(
        "ticket_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE", name="fk_ticket_embeddings_ticket_id_tickets"),
            nullable=False,
        ),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=False),
        sa.Column("resolution_summary", sa.Text(), nullable=False),
        *timestamps(include_updated=False),
        sa.UniqueConstraint("ticket_id", name="uq_ticket_embeddings_ticket_id"),
    )

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding_model", sa.String(120), nullable=False, server_default=""),
        *timestamps(),
    )
    op.create_index("ix_knowledge_documents_filename", "knowledge_documents", ["filename"])

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey(
                "knowledge_documents.id", ondelete="CASCADE", name="fk_knowledge_chunks_document_id_knowledge_documents"
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        *timestamps(include_updated=False),
    )
    op.create_index(
        "ix_knowledge_chunks_document_id_chunk_index",
        "knowledge_chunks",
        ["document_id", "chunk_index"],
        unique=True,
    )

    # HNSW indexes make cosine-distance ORDER BY queries fast as the tables grow.
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding_hnsw ON knowledge_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX ix_ticket_embeddings_embedding_hnsw ON ticket_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ticket_embeddings_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
    op.drop_table("ticket_embeddings")
    op.drop_table("ticket_events")
    op.drop_table("ticket_messages")
    op.drop_table("ai_feedback")
    op.drop_table("ai_responses")
    op.drop_table("tickets")
    op.drop_table("users")

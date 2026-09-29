"""Development seed data.

Usage (from backend/):
    python -m app.scripts.seed           # idempotent: only adds what is missing
    python -m app.scripts.seed --reset   # wipe all data first

Users and tickets are created once. Knowledge documents and resolved-ticket embeddings are
(re)attempted on every run, so if Ollama was offline the first time just run the seed again.
"""

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingError, get_embedding_provider
from app.ai.similar_tickets import resolved_ticket_text
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal
from app.models import (
    KnowledgeDocument,
    MessageType,
    Ticket,
    TicketCategory,
    TicketEmbedding,
    TicketEventType,
    TicketMessage,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)
from app.services.event_service import record_event
from app.services.knowledge_service import ingest_document, validate_upload

ADMIN_PASSWORD = "Admin123!"
AGENT_PASSWORD = "Agent123!"
CUSTOMER_PASSWORD = "Customer123!"

USERS = [
    ("Ada Admin", "admin@supportdesk.dev", UserRole.ADMIN, ADMIN_PASSWORD),
    ("Alice Agent", "alice@supportdesk.dev", UserRole.AGENT, AGENT_PASSWORD),
    ("Bob Agent", "bob@supportdesk.dev", UserRole.AGENT, AGENT_PASSWORD),
    ("Carol Customer", "carol@customer.dev", UserRole.CUSTOMER, CUSTOMER_PASSWORD),
    ("Dave Customer", "dave@customer.dev", UserRole.CUSTOMER, CUSTOMER_PASSWORD),
    ("Erin Customer", "erin@customer.dev", UserRole.CUSTOMER, CUSTOMER_PASSWORD),
]


@dataclass
class SeedTicket:
    customer: str
    subject: str
    description: str
    environment: str
    status: TicketStatus
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    agent: str | None = None
    days_ago: float = 1
    resolution: str | None = None
    resolved_after_hours: float | None = None
    replies: tuple[tuple[str, str], ...] = ()


TICKETS = [
    SeedTicket(
        customer="carol@customer.dev",
        subject="API returns 401 Unauthorized with new key",
        description=(
            "We created a new API key this morning and every request to /v2/projects returns "
            "401 Unauthorized. The old key still works. We're sending it in the Authorization header."
        ),
        environment="production",
        status=TicketStatus.RESOLVED,
        category=TicketCategory.API,
        priority=TicketPriority.HIGH,
        agent="alice@supportdesk.dev",
        days_ago=20,
        resolution=(
            "The customer had created a sandbox key (ak_test_) and was calling production. "
            "Creating a production key with prefix ak_live_ resolved the 401 errors."
        ),
        resolved_after_hours=3,
        replies=(
            ("alice@supportdesk.dev", "Could you confirm the prefix of the new key? Sandbox keys start with ak_test_."),
            ("carol@customer.dev", "It starts with ak_test_. That explains it, thanks!"),
        ),
    ),
    SeedTicket(
        customer="dave@customer.dev",
        subject="Charged twice for March invoice",
        description="My credit card statement shows two charges of $49 for the March invoice INV-2031.",
        environment="production",
        status=TicketStatus.RESOLVED,
        category=TicketCategory.BILLING,
        priority=TicketPriority.MEDIUM,
        agent="bob@supportdesk.dev",
        days_ago=15,
        resolution=(
            "One of the charges was a pending card authorization, not a settled charge. It dropped off "
            "the statement within 3 business days. No refund was necessary."
        ),
        resolved_after_hours=26,
    ),
    SeedTicket(
        customer="erin@customer.dev",
        subject="Locked out after too many login attempts",
        description="I typed my password wrong a few times and now I can't log in at all. It says account locked.",
        environment="production",
        status=TicketStatus.CLOSED,
        category=TicketCategory.AUTHENTICATION,
        priority=TicketPriority.MEDIUM,
        agent="alice@supportdesk.dev",
        days_ago=12,
        resolution=(
            "Account was locked after 5 failed attempts. Cleared the lockout from the admin console and "
            "the customer reset their password using the Forgot password link."
        ),
        resolved_after_hours=1.5,
    ),
    SeedTicket(
        customer="carol@customer.dev",
        subject="SSO login fails with INVALID_AUDIENCE",
        description="After switching identity providers, SAML login fails with error INVALID_AUDIENCE for all users.",
        environment="production",
        status=TicketStatus.RESOLVED,
        category=TicketCategory.AUTHENTICATION,
        priority=TicketPriority.CRITICAL,
        agent="bob@supportdesk.dev",
        days_ago=8,
        resolution=(
            "The Audience URI in the new identity provider was set to the old tenant URL. Updating it to "
            "https://app.acme-cloud.dev/saml/metadata fixed SSO for all users."
        ),
        resolved_after_hours=2,
    ),
    SeedTicket(
        customer="dave@customer.dev",
        subject="Getting 429 Too Many Requests from the API",
        description=(
            "Our nightly sync job started failing with 429 Too Many Requests after we added more projects. "
            "We are on the Starter plan."
        ),
        environment="production",
        status=TicketStatus.RESOLVED,
        category=TicketCategory.API,
        priority=TicketPriority.MEDIUM,
        agent="alice@supportdesk.dev",
        days_ago=6,
        resolution=(
            "The job exceeded the Starter limit of 100 requests per minute. Customer added backoff using "
            "the X-RateLimit-Reset header and throttled the job to 90 requests per minute."
        ),
        resolved_after_hours=20,
    ),
    SeedTicket(
        customer="carol@customer.dev",
        subject="Dashboard is extremely slow to load",
        description="The projects dashboard takes more than 40 seconds to load since yesterday. Other pages are fine.",
        environment="production",
        status=TicketStatus.IN_PROGRESS,
        category=TicketCategory.PERFORMANCE,
        priority=TicketPriority.HIGH,
        agent="alice@supportdesk.dev",
        days_ago=1.5,
        replies=(("alice@supportdesk.dev", "Thanks for reporting. Does the issue also happen in a private window?"),),
    ),
    SeedTicket(
        customer="erin@customer.dev",
        subject="Payment failed but card is valid",
        description=(
            "We got an email that our payment failed and there's a red banner in the dashboard. "
            "The card is valid and has funds. What should we do?"
        ),
        environment="production",
        status=TicketStatus.WAITING_FOR_CUSTOMER,
        category=TicketCategory.BILLING,
        priority=TicketPriority.HIGH,
        agent="bob@supportdesk.dev",
        days_ago=1,
        replies=(
            ("bob@supportdesk.dev", "Could you share the invoice number and the last four digits of the card?"),
        ),
    ),
    SeedTicket(
        customer="dave@customer.dev",
        subject="Webhook events not arriving on staging",
        description=(
            "We configured a webhook endpoint on our staging server but haven't received any events "
            "for the last two days."
        ),
        environment="staging",
        status=TicketStatus.OPEN,
        days_ago=0.4,
    ),
    SeedTicket(
        customer="carol@customer.dev",
        subject="Feature request: export tickets to CSV",
        description="It would be great to export all our workspace tickets to CSV for monthly reporting.",
        environment="production",
        status=TicketStatus.OPEN,
        days_ago=0.2,
    ),
    SeedTicket(
        customer="erin@customer.dev",
        subject="MFA codes always invalid",
        description="Since getting a new phone every authenticator code I enter is rejected as invalid.",
        environment="production",
        status=TicketStatus.OPEN,
        days_ago=0.1,
    ),
]


def reset_database(db: Session) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    print("Database wiped.")


def seed_users(db: Session) -> dict[str, User]:
    users: dict[str, User] = {}
    for name, email, role, password in USERS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(name=name, email=email, role=role, password_hash=hash_password(password))
            db.add(user)
            print(f"  + user {email} ({role.value})")
        users[email] = user
    db.commit()
    return users


def seed_tickets(db: Session, users: dict[str, User]) -> None:
    if db.scalar(select(Ticket.id).limit(1)) is not None:
        print("  tickets already exist, skipping")
        return
    now = datetime.now(timezone.utc)
    for spec in TICKETS:
        created_at = now - timedelta(days=spec.days_ago)
        customer = users[spec.customer]
        agent = users[spec.agent] if spec.agent else None
        ticket = Ticket(
            customer_id=customer.id,
            assigned_agent_id=agent.id if agent else None,
            subject=spec.subject,
            description=spec.description,
            environment=spec.environment,
            status=spec.status,
            category=spec.category,
            priority=spec.priority,
            created_at=created_at,
            updated_at=created_at,
        )
        if spec.resolution and spec.resolved_after_hours is not None:
            ticket.resolution_summary = spec.resolution
            ticket.resolved_at = created_at + timedelta(hours=spec.resolved_after_hours)
            ticket.updated_at = ticket.resolved_at
        db.add(ticket)
        db.flush()

        db.add(
            TicketMessage(
                ticket_id=ticket.id,
                sender_id=customer.id,
                message=spec.description,
                message_type=MessageType.CUSTOMER,
                created_at=created_at,
            )
        )
        record_event(db, ticket.id, TicketEventType.TICKET_CREATED, {"customer_id": customer.id, "seed": True})
        for offset, (sender_email, text) in enumerate(spec.replies, start=1):
            sender = users[sender_email]
            db.add(
                TicketMessage(
                    ticket_id=ticket.id,
                    sender_id=sender.id,
                    message=text,
                    message_type=MessageType.CUSTOMER if sender.role == UserRole.CUSTOMER else MessageType.AGENT,
                    created_at=created_at + timedelta(minutes=30 * offset),
                )
            )
        if ticket.resolved_at:
            db.add(
                TicketMessage(
                    ticket_id=ticket.id,
                    sender_id=agent.id if agent else None,
                    message=f"Ticket marked as resolved: {spec.resolution}",
                    message_type=MessageType.SYSTEM,
                    created_at=ticket.resolved_at,
                )
            )
            record_event(db, ticket.id, TicketEventType.TICKET_RESOLVED, {"seed": True})
        print(f"  + ticket #{ticket.id} {spec.subject}")
    db.commit()


def seed_knowledge(db: Session) -> None:
    knowledge_dir = Path(get_settings().KNOWLEDGE_DIR)
    if not knowledge_dir.is_dir():
        print(f"  knowledge directory not found: {knowledge_dir}")
        return
    embedder = get_embedding_provider()
    existing = set(db.scalars(select(KnowledgeDocument.filename)).all())
    for path in sorted(knowledge_dir.glob("*")):
        if path.suffix.lower() not in (".md", ".txt") or path.name in existing:
            continue
        try:
            filename, content_type, text = validate_upload(path.name, "", path.read_bytes())
            document = ingest_document(db, embedder, filename, content_type, text)
            print(f"  + knowledge '{document.title}' ({len(document.chunks)} chunks)")
        except AppError as exc:
            db.rollback()
            print(f"  ! could not ingest {path.name}: {exc.message}")


def seed_resolved_ticket_embeddings(db: Session) -> None:
    embedder = get_embedding_provider()
    tickets = db.scalars(
        select(Ticket)
        .outerjoin(TicketEmbedding, TicketEmbedding.ticket_id == Ticket.id)
        .where(
            Ticket.status.in_((TicketStatus.RESOLVED, TicketStatus.CLOSED)),
            Ticket.resolution_summary.is_not(None),
            TicketEmbedding.id.is_(None),
        )
    ).all()
    for ticket in tickets:
        try:
            vector = embedder.embed(
                [resolved_ticket_text(ticket.subject, ticket.description, ticket.resolution_summary or "")]
            )[0]
        except EmbeddingError as exc:
            print(f"  ! could not embed ticket #{ticket.id}: {exc}")
            return
        db.add(TicketEmbedding(ticket_id=ticket.id, embedding=vector, resolution_summary=ticket.resolution_summary))
        print(f"  + embedding for resolved ticket #{ticket.id}")
    db.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed development data")
    parser.add_argument("--reset", action="store_true", help="delete all existing data first")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.reset:
            reset_database(db)
        print("Seeding users...")
        users = seed_users(db)
        print("Seeding tickets...")
        seed_tickets(db, users)
        print("Seeding knowledge base...")
        seed_knowledge(db)
        print("Indexing resolved tickets...")
        seed_resolved_ticket_embeddings(db)

    print("\nDone. Development accounts:")
    for name, email, role, password in USERS:
        print(f"  {role.value:<8} {email:<26} {password}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

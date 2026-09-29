"""Test configuration.

Tests run against an in-memory SQLite database so they need no running services.
Vector search falls back to Python cosine similarity on SQLite; the PostgreSQL/pgvector
path is exercised when running the app itself.
"""

import os

os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret-key-for-pytest-only-0123456789",
        "EMBEDDING_PROVIDER": "hash",
        "REDIS_URL": "",
        "AI_AUTO_ANALYZE": "false",
        "RATE_LIMIT_ENABLED": "false",
        "LOG_LEVEL": "WARNING",
        "RETRIEVAL_MIN_SIMILARITY": "0.05",
    }
)

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401
from app.ai.classifier import ClassificationOutput  # noqa: E402
from app.ai.ollama_client import MalformedAIOutputError, get_llm_client  # noqa: E402
from app.ai.priority import PriorityOutput  # noqa: E402
from app.ai.response_generator import ResponseOutput  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db, get_session_factory  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User, UserRole  # noqa: E402
from app.services import progress_service  # noqa: E402

TEST_PASSWORD = "Password123!"


class FakeLLM:
    """Deterministic stand-in for Ollama."""

    model_name = "fake-llm"

    def __init__(self, available: bool = True, malformed: set[type[BaseModel]] | None = None) -> None:
        self.available = available
        self.malformed = malformed or set()
        self.calls: list[type[BaseModel]] = []
        self.response_sources = ["API Keys, Authentication and Rate Limits", "Totally Invented Handbook"]

    def is_available(self) -> bool:
        return self.available

    def unavailable_message(self) -> str:
        return "Ollama is not reachable at http://localhost:11434 (test)"

    def generate_structured(self, system_prompt: str, user_prompt: str, schema: type[BaseModel]):
        self.calls.append(schema)
        if schema in self.malformed:
            raise MalformedAIOutputError("bad json")
        if schema is ClassificationOutput:
            return ClassificationOutput(category="API", confidence=0.91)
        if schema is PriorityOutput:
            return PriorityOutput(priority="HIGH", reason="Production API calls are failing.", confidence=0.8)
        if schema is ResponseOutput:
            return ResponseOutput(
                draft_response="Please confirm your key starts with ak_live_ for production requests.",
                reasoning_summary="Knowledge base explains key prefixes per environment.",
                confidence=0.82,
                requires_more_information=False,
                requested_information=[],
                source_references=self.response_sources,
            )
        raise AssertionError(f"Unexpected schema {schema}")


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db(session_factory) -> Iterator[Session]:
    session = session_factory()
    yield session
    session.close()


@pytest.fixture()
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture()
def client(session_factory, fake_llm) -> Iterator[TestClient]:
    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    app.dependency_overrides[get_llm_client] = lambda: fake_llm
    progress_service._memory_store.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_user(db: Session, name: str, email: str, role: UserRole) -> User:
    user = User(name=name, email=email, role=role, password_hash=hash_password(TEST_PASSWORD))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def customer(db) -> User:
    return _create_user(db, "Carol Customer", "carol@customer.dev", UserRole.CUSTOMER)


@pytest.fixture()
def other_customer(db) -> User:
    return _create_user(db, "Dave Customer", "dave@customer.dev", UserRole.CUSTOMER)


@pytest.fixture()
def agent(db) -> User:
    return _create_user(db, "Alice Agent", "alice@supportdesk.dev", UserRole.AGENT)


@pytest.fixture()
def admin(db) -> User:
    return _create_user(db, "Ada Admin", "admin@supportdesk.dev", UserRole.ADMIN)


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}


def create_ticket(client: TestClient, customer: User, **overrides) -> dict:
    payload = {
        "subject": "API returns 401 with new key",
        "description": "Every request to /v2/projects returns 401 Unauthorized since we rotated the API key.",
        "environment": "production",
        **overrides,
    }
    response = client.post("/api/tickets", json=payload, headers=auth_headers(customer))
    assert response.status_code == 201, response.text
    return response.json()

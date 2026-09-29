from collections.abc import Callable, Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

SessionFactory = Callable[[], Session]

engine = create_engine(get_settings().DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session_factory() -> SessionFactory:
    """Session factory for work that outlives the request (background AI jobs)."""
    return SessionLocal

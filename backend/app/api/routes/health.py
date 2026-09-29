from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai.ollama_client import LLMClient, get_llm_client
from app.core.config import get_settings
from app.core.redis_client import redis_ping
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db), llm: LLMClient = Depends(get_llm_client)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        database_ok = True
    except Exception:  # noqa: BLE001
        database_ok = False
    settings = get_settings()
    return {
        "status": "ok" if database_ok else "degraded",
        "database": database_ok,
        "redis": redis_ping(),
        "ollama": llm.is_available(),
        "ollama_model": llm.model_name,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL if settings.EMBEDDING_PROVIDER == "ollama" else "hash",
    }

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings loaded from environment variables (and an optional .env file)."""

    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "AI Support Engineer Platform"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql+psycopg://support:support@localhost:5432/support_platform"

    JWT_SECRET_KEY: str = Field(default="dev-only-insecure-secret-change-me-in-env-file", min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    FRONTEND_URL: str = "http://localhost:5173"
    CORS_EXTRA_ORIGINS: str = ""

    REDIS_URL: str = "redis://localhost:6379/0"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    OLLAMA_TIMEOUT_SECONDS: float = 120.0

    EMBEDDING_PROVIDER: Literal["ollama", "hash"] = "ollama"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSION: int = 768

    AI_AUTO_ANALYZE: bool = True
    RAG_TOP_K: int = 4
    SIMILAR_TICKETS_TOP_K: int = 3
    # Results below this cosine similarity are treated as unrelated and not shown to the model.
    RETRIEVAL_MIN_SIMILARITY: float = 0.3
    CHUNK_SIZE: int = 900
    CHUNK_OVERLAP: int = 150

    MAX_UPLOAD_BYTES: int = 1_000_000
    KNOWLEDGE_DIR: str = str(REPO_ROOT / "knowledge")

    RATE_LIMIT_ENABLED: bool = True
    AUTH_RATE_LIMIT_PER_MINUTE: int = 20

    @field_validator("CHUNK_OVERLAP")
    @classmethod
    def overlap_smaller_than_chunk(cls, value: int, info) -> int:
        chunk_size = info.data.get("CHUNK_SIZE", 900)
        if value >= chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return value

    @property
    def cors_origins(self) -> list[str]:
        origins = {self.FRONTEND_URL.rstrip("/")}
        origins.update(o.strip().rstrip("/") for o in self.CORS_EXTRA_ORIGINS.split(",") if o.strip())
        return sorted(origins)


@lru_cache
def get_settings() -> Settings:
    return Settings()

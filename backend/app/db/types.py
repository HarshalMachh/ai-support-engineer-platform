from enum import Enum as PyEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Enum
from sqlalchemy.dialects.postgresql import JSONB

from app.core.config import get_settings

# JSONB on PostgreSQL, plain JSON elsewhere (SQLite is used by the test-suite).
JSONType = JSON().with_variant(JSONB(), "postgresql")


def string_enum(enum_cls: type[PyEnum], length: int = 32) -> Enum:
    """Store enums as VARCHAR so adding values never requires ALTER TYPE migrations."""
    return Enum(
        enum_cls,
        native_enum=False,
        length=length,
        validate_strings=True,
        values_callable=lambda members: [m.value for m in members],
    )


def embedding_vector() -> Vector:
    return Vector(get_settings().EMBEDDING_DIMENSION)

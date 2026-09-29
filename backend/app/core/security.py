from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

# bcrypt only uses the first 72 bytes of a password; longer inputs are rejected by schemas.
BCRYPT_MAX_BYTES = 72


class TokenError(Exception):
    """Raised when a JWT cannot be decoded or validated."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:BCRYPT_MAX_BYTES], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:BCRYPT_MAX_BYTES], password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: int, role: str, expires_minutes: int | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire_after = expires_minutes if expires_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expire_after),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid authentication token") from exc

    if payload.get("type") != "access" or not str(payload.get("sub", "")).isdigit():
        raise TokenError("Invalid authentication token")
    return payload

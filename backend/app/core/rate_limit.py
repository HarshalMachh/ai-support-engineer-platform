"""Fixed-window rate limiting backed by Redis (fails open if Redis is unavailable)."""

import time

import redis
from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import RateLimitedError
from app.core.redis_client import get_redis, mark_unavailable


def check_rate_limit(bucket: str, identifier: str, limit: int, window_seconds: int = 60) -> None:
    settings = get_settings()
    if not settings.RATE_LIMIT_ENABLED:
        return
    client = get_redis()
    if client is None:
        return

    window = int(time.time() // window_seconds)
    key = f"ratelimit:{bucket}:{identifier}:{window}"
    try:
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        count, _ = pipe.execute()
    except redis.RedisError as exc:
        mark_unavailable(exc)
        return

    if int(count) > limit:
        raise RateLimitedError("Too many requests. Please wait a minute and try again.")


def auth_rate_limit(request: Request) -> None:
    """FastAPI dependency limiting login/register attempts per client IP."""
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit("auth", client_ip, get_settings().AUTH_RATE_LIMIT_PER_MINUTE)

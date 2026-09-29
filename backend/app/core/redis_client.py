"""Thin Redis wrapper that degrades gracefully when Redis is not reachable.

Redis is used for caching (embeddings, analytics), AI progress events and rate limiting.
Every helper returns a neutral value instead of raising when Redis is down, so the
application keeps working in development without Redis.
"""

import threading
import time

import redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

RETRY_AFTER_FAILURE_SECONDS = 30.0

_client: redis.Redis | None = None
_unavailable_until = 0.0
_lock = threading.Lock()


def get_redis() -> redis.Redis | None:
    """Return a connected Redis client, or None if Redis is disabled/unavailable."""
    global _client, _unavailable_until
    url = get_settings().REDIS_URL
    if not url:
        return None
    if time.monotonic() < _unavailable_until:
        return None

    with _lock:
        if _client is None:
            _client = redis.Redis.from_url(
                url,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=1.0,
            )
    return _client


def mark_unavailable(error: Exception) -> None:
    global _unavailable_until
    if time.monotonic() >= _unavailable_until:
        logger.warning(
            "Redis unavailable, continuing without it",
            extra={"operation": "redis", "success": False, "error": str(error)},
        )
    _unavailable_until = time.monotonic() + RETRY_AFTER_FAILURE_SECONDS


def redis_ping() -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except redis.RedisError as exc:
        mark_unavailable(exc)
        return False


def cache_get(key: str) -> str | None:
    client = get_redis()
    if client is None:
        return None
    try:
        return client.get(key)
    except redis.RedisError as exc:
        mark_unavailable(exc)
        return None


def cache_set(key: str, value: str, ttl_seconds: int) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        client.set(key, value, ex=ttl_seconds)
    except redis.RedisError as exc:
        mark_unavailable(exc)


def cache_delete_prefix(prefix: str) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        for key in client.scan_iter(match=f"{prefix}*", count=100):
            client.delete(key)
    except redis.RedisError as exc:
        mark_unavailable(exc)

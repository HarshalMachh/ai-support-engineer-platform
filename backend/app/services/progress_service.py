"""Live AI progress events per ticket.

Events are stored in Redis (shared across workers) with an in-process fallback so the
feature still works in single-process development without Redis.
"""

import json
import threading
from datetime import datetime, timezone
from typing import Any

import redis

from app.core.redis_client import get_redis, mark_unavailable

PROGRESS_TTL_SECONDS = 60 * 60
MAX_EVENTS = 50

_memory_store: dict[int, list[dict[str, Any]]] = {}
_memory_lock = threading.Lock()


def _key(ticket_id: int) -> str:
    return f"ai_progress:{ticket_id}"


def reset_progress(ticket_id: int) -> None:
    with _memory_lock:
        _memory_store[ticket_id] = []
    client = get_redis()
    if client is None:
        return
    try:
        client.delete(_key(ticket_id))
    except redis.RedisError as exc:
        mark_unavailable(exc)


def publish_progress(ticket_id: int, event: str, message: str) -> None:
    entry = {"event": event, "message": message, "timestamp": datetime.now(timezone.utc).isoformat()}
    with _memory_lock:
        events = _memory_store.setdefault(ticket_id, [])
        events.append(entry)
        del events[:-MAX_EVENTS]
    client = get_redis()
    if client is None:
        return
    try:
        pipe = client.pipeline()
        pipe.rpush(_key(ticket_id), json.dumps(entry))
        pipe.ltrim(_key(ticket_id), -MAX_EVENTS, -1)
        pipe.expire(_key(ticket_id), PROGRESS_TTL_SECONDS)
        pipe.execute()
    except redis.RedisError as exc:
        mark_unavailable(exc)


def get_progress(ticket_id: int) -> list[dict[str, Any]]:
    client = get_redis()
    if client is not None:
        try:
            raw_events = client.lrange(_key(ticket_id), 0, -1)
            if raw_events:
                return [json.loads(raw) for raw in raw_events]
        except redis.RedisError as exc:
            mark_unavailable(exc)
    with _memory_lock:
        return list(_memory_store.get(ticket_id, []))

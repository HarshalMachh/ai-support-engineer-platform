import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)

# Keys that must never be written to logs, even if passed via `extra`.
REDACTED_KEYS = {"password", "password_hash", "token", "access_token", "authorization", "jwt", "secret"}

STRUCTURED_FIELDS = ("operation", "ticket_id", "latency_ms", "success", "error", "method", "path", "status_code")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        user_id = user_id_var.get()
        if request_id:
            entry["request_id"] = request_id
        if user_id is not None:
            entry["user_id"] = user_id

        for field in STRUCTURED_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                entry[field] = value

        extra_context = getattr(record, "context", None)
        if isinstance(extra_context, dict):
            for key, value in extra_context.items():
                entry[key] = "[REDACTED]" if key.lower() in REDACTED_KEYS else value

        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # Uvicorn's access log duplicates our request middleware log.
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

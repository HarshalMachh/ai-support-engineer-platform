"""Minimal synchronous client for a locally running Ollama server."""

import json
import time
from typing import Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class OllamaUnavailableError(Exception):
    """Ollama is not running, not reachable, or the requested model is not pulled."""


class MalformedAIOutputError(Exception):
    """The model returned output that does not match the requested JSON schema."""


class LLMClient(Protocol):
    model_name: str

    def is_available(self) -> bool: ...

    def unavailable_message(self) -> str: ...

    def generate_structured(self, system_prompt: str, user_prompt: str, schema: type[SchemaT]) -> SchemaT: ...


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = model or settings.OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds or settings.OLLAMA_TIMEOUT_SECONDS

    def is_available(self) -> bool:
        """True when the server responds and the configured model is pulled."""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=3.0)
            response.raise_for_status()
        except httpx.HTTPError:
            return False
        models = {m.get("name", "") for m in response.json().get("models", [])}
        return any(name == self.model_name or name.split(":")[0] == self.model_name for name in models)

    def unavailable_message(self) -> str:
        return (
            f"Ollama is not reachable at {self.base_url} or the model '{self.model_name}' is not pulled. "
            f"Start Ollama and run: ollama pull {self.model_name}"
        )

    def generate_structured(self, system_prompt: str, user_prompt: str, schema: type[SchemaT]) -> SchemaT:
        """Ask the model for JSON matching `schema`; retries once on malformed output."""
        last_error: Exception | None = None
        for attempt in range(2):
            raw = self._chat(system_prompt, user_prompt, schema.model_json_schema())
            try:
                return schema.model_validate(json.loads(raw))
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "Malformed structured output from model",
                    extra={"operation": "ollama.generate", "success": False, "error": str(exc)[:300]},
                    exc_info=False,
                )
                user_prompt = (
                    f"{user_prompt}\n\nYour previous answer was not valid JSON for the schema. "
                    "Reply with ONLY a JSON object that matches the schema."
                )
        raise MalformedAIOutputError(f"Model returned malformed output after retry: {last_error}")

    def _chat(self, system_prompt: str, user_prompt: str, json_schema: dict) -> str:
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": json_schema,
            "stream": False,
            # num_ctx must stay small. Qwen's default 32k context allocates a buffer
            # that crashes llama-server on 8 GB Windows machines (exit 0xc0000409).
            "options": {"temperature": 0.1, "num_ctx": 4096},
        }
        started = time.perf_counter()
        try:
            response = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout_seconds)
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(self.unavailable_message()) from exc

        latency_ms = round((time.perf_counter() - started) * 1000)
        if response.status_code == 404:
            raise OllamaUnavailableError(self.unavailable_message())
        if response.status_code >= 400:
            raise OllamaUnavailableError(f"Ollama returned HTTP {response.status_code}: {response.text[:200]}")

        logger.info(
            "Ollama chat completed",
            extra={"operation": "ollama.chat", "latency_ms": latency_ms, "success": True},
        )
        return response.json().get("message", {}).get("content", "")


def get_llm_client() -> LLMClient:
    """FastAPI dependency; overridden in tests with a fake client."""
    return OllamaClient()

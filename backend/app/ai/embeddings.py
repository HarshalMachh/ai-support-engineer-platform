"""Local embedding providers.

- ``ollama``: calls Ollama's /api/embed endpoint (default model: nomic-embed-text, 768 dims).
- ``hash``: deterministic feature-hashing embeddings. No model required; useful for tests and
  for exploring the app without Ollama. Retrieval quality is keyword-level only.
"""

import hashlib
import json
import math
import re
from typing import Protocol

import httpx

from app.core.config import get_settings
from app.core.redis_client import cache_get, cache_set

EMBEDDING_CACHE_TTL_SECONDS = 60 * 60 * 24


class EmbeddingError(Exception):
    """Embeddings could not be generated."""


class EmbeddingProvider(Protocol):
    model_name: str
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OllamaEmbeddingProvider:
    def __init__(self, base_url: str, model: str, dimension: int, timeout_seconds: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model
        self.dimension = dimension
        self.timeout_seconds = timeout_seconds

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float] | None] = []
        missing: list[tuple[int, str]] = []
        for index, text in enumerate(texts):
            cached = cache_get(self._cache_key(text))
            results.append(json.loads(cached) if cached else None)
            if cached is None:
                missing.append((index, text))

        if missing:
            vectors = self._request([text for _, text in missing])
            for (index, text), vector in zip(missing, vectors, strict=True):
                results[index] = vector
                cache_set(self._cache_key(text), json.dumps(vector), EMBEDDING_CACHE_TTL_SECONDS)
        return [vector for vector in results if vector is not None]

    def _request(self, texts: list[str]) -> list[list[float]]:
        try:
            response = httpx.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model_name, "input": texts},
                timeout=self.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise EmbeddingError(
                f"Could not reach Ollama at {self.base_url} for embeddings. "
                f"Start Ollama and run: ollama pull {self.model_name}"
            ) from exc
        if response.status_code >= 400:
            raise EmbeddingError(
                f"Ollama embedding request failed (HTTP {response.status_code}). "
                f"Is the model pulled? Run: ollama pull {self.model_name}"
            )
        vectors = response.json().get("embeddings") or []
        if len(vectors) != len(texts):
            raise EmbeddingError("Ollama returned an unexpected number of embeddings")
        for vector in vectors:
            if len(vector) != self.dimension:
                raise EmbeddingError(
                    f"Embedding dimension mismatch: model returned {len(vector)}, "
                    f"EMBEDDING_DIMENSION is {self.dimension}"
                )
        return vectors

    def _cache_key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"embedding:{self.model_name}:{digest}"


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class HashEmbeddingProvider:
    """Bag-of-words feature hashing with unigrams and bigrams, L2-normalised."""

    def __init__(self, dimension: int) -> None:
        self.model_name = "hash-embedding"
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = TOKEN_PATTERN.findall(text.lower())
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        for feature in features:
            digest = hashlib.md5(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "little") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            vector[0] = 1.0
            return vector
        return [v / norm for v in vector]


def get_embedding_provider() -> EmbeddingProvider:
    """FastAPI dependency returning the configured provider."""
    settings = get_settings()
    if settings.EMBEDDING_PROVIDER == "hash":
        return HashEmbeddingProvider(settings.EMBEDDING_DIMENSION)
    return OllamaEmbeddingProvider(
        settings.OLLAMA_BASE_URL, settings.EMBEDDING_MODEL, settings.EMBEDDING_DIMENSION
    )


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

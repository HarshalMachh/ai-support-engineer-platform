#!/usr/bin/env sh
# One-shot local setup: env file, Ollama models, containers, migrations, seed data.
set -e

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example (edit JWT_SECRET_KEY before sharing this machine)."
fi

MODEL=$(grep -E '^OLLAMA_MODEL=' .env | cut -d= -f2)
EMBED_MODEL=$(grep -E '^EMBEDDING_MODEL=' .env | cut -d= -f2)

if command -v ollama >/dev/null 2>&1; then
  echo "Pulling Ollama models: ${MODEL:-qwen2.5:7b} and ${EMBED_MODEL:-nomic-embed-text}"
  ollama pull "${MODEL:-qwen2.5:7b}"
  ollama pull "${EMBED_MODEL:-nomic-embed-text}"
else
  echo "WARNING: ollama not found. Install it from https://ollama.com, then run:"
  echo "  ollama pull ${MODEL:-qwen2.5:7b} && ollama pull ${EMBED_MODEL:-nomic-embed-text}"
fi

docker compose up -d --build
echo "Waiting for the backend to become healthy..."
until curl -sf http://localhost:8000/api/health >/dev/null; do sleep 2; done

docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed

echo ""
echo "Ready! Frontend: http://localhost:5173  API docs: http://localhost:8000/docs"

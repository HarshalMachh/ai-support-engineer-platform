# AI Support Engineer Platform

A production-style, full-stack customer support platform with a **local, human-in-the-loop AI assistant**.
Think of it as a simplified Zendesk/Intercom where every new ticket is automatically triaged by an AI that
classifies it, sets a priority, searches the documentation (RAG), finds similar solved tickets and drafts a
reply with its sources — and then **stops and waits for a human agent** to approve, edit, reject or
regenerate that draft.

Everything is free and runs locally: **Ollama** for inference and embeddings, **PostgreSQL + pgvector** for
storage and vector search, **LangGraph** for the AI workflow. No OpenAI/Anthropic/Gemini/Pinecone or other paid services.

---

## Table of contents

- [Problem being solved](#problem-being-solved)
- [Features](#features)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [AI workflow](#ai-workflow)
- [RAG explained](#rag-explained)
- [Human in the loop](#human-in-the-loop)
- [Screenshots](#screenshots)
- [Setup requirements](#setup-requirements)
- [Quick start with Docker](#quick-start-with-docker)
- [Ollama setup](#ollama-setup)
- [Local setup without Docker](#local-setup-without-docker)
- [Environment variables](#environment-variables)
- [Database and migrations](#database-and-migrations)
- [Seed data and sample accounts](#seed-data-and-sample-accounts)
- [Running tests](#running-tests)
- [API overview](#api-overview)
- [Project structure](#project-structure)
- [Known limitations](#known-limitations)
- [Future improvements](#future-improvements)

---

## Problem being solved

Support teams spend a lot of time on repetitive triage: reading a ticket, deciding what it is about, how
urgent it is, searching internal docs, remembering how a similar ticket was solved and writing a reply.
LLMs can do much of this, but letting a model reply to customers directly is risky: it can hallucinate
policies, cite sources that don't exist, or mishandle sensitive situations.

This project shows how to get the productivity benefit **without giving up control**:

- the AI does the triage and drafting work in the background,
- every claim is grounded in retrieved documentation or previously resolved tickets,
- unsupported sources are stripped automatically, and missing information is requested instead of invented,
- a human agent is always the one who sends the reply.

## Features

**Customers**
- Register, log in / out, view profile
- Create tickets (subject, description, environment)
- View only their own tickets, open ticket details, reply, see status and agent responses
- Close a ticket; replying to a resolved ticket reopens it

**Support agents**
- Ticket queue with filters (status, priority, category, assignee), debounced search (text or `#id`), pagination
- Ticket detail: assign to self, change status/priority/category, manual replies, resolve with a summary
- AI panel: classification + confidence, priority + reasoning, response confidence, live workflow progress,
  retrieved documentation chunks (with similarity), similar resolved tickets, suggested reply
- Approve, edit, reject (with reason) or regenerate the AI draft; rate drafts 1–5

**Admins**
- Everything agents can do
- View users / agents / customers
- Knowledge base management: upload `.md`/`.txt`, view chunks, delete, test semantic search
- Analytics: ticket metrics (by status/priority/category, average resolution time) and AI metrics
  (approved / edited / rejected counts, approval & acceptance rates, feedback rating)

**Engineering**
- JWT auth with bcrypt password hashing, role-based access control, customer ticket isolation
- Service layer architecture (routes contain no business logic)
- Structured JSON logging with `request_id`, `user_id`, `ticket_id`, `operation`, `latency_ms`, `success`, `error`
- Graceful degradation: Ollama offline, Redis offline, malformed model output, embedding failure, DB errors
- Background AI processing with FastAPI `BackgroundTasks`, live progress via WebSocket (with polling fallback)
- Redis for embedding cache, progress events and login rate limiting (fail-open when unavailable)
- 52 backend tests (pytest) and 20 frontend tests (Vitest + React Testing Library)

## Architecture

```mermaid
flowchart LR
    subgraph Browser
        UI["React + TypeScript (Vite, Tailwind)<br/>TanStack Query · Auth Context"]
    end

    subgraph Backend["FastAPI backend"]
        API["REST routes /api/*<br/>WebSocket /api/ws/*"]
        SVC["Service layer<br/>tickets · ai · knowledge · analytics"]
        AI["AI module (LangGraph)<br/>classify → priority → RAG → similar → draft → pause"]
        BG["BackgroundTasks"]
    end

    PG[("PostgreSQL + pgvector<br/>tickets, messages, AI responses,<br/>knowledge chunks, ticket embeddings")]
    RD[("Redis<br/>cache · progress · rate limit")]
    OL["Ollama (local)<br/>qwen2.5:7b · nomic-embed-text"]

    UI -- "REST (JWT)" --> API
    UI -. "WebSocket progress" .-> API
    API --> SVC
    SVC --> PG
    SVC --> RD
    SVC --> BG --> AI
    AI -- "structured JSON chat" --> OL
    AI -- "embeddings" --> OL
    AI -- "vector search" --> PG
```

The frontend and backend are separate applications. The backend follows a layered design:

| Layer | Location | Responsibility |
| --- | --- | --- |
| Routes | `backend/app/api/routes/` | HTTP parsing, dependencies (auth/roles), response models |
| Services | `backend/app/services/` | Business rules, transactions, authorization details |
| AI | `backend/app/ai/` | LangGraph workflow, prompts, Ollama client, embeddings, retrieval |
| Models / schemas | `backend/app/models/`, `backend/app/schemas/` | SQLAlchemy ORM and Pydantic contracts |

## Technology stack

| Area | Technology |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, Axios |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Database | PostgreSQL 16 + pgvector (HNSW cosine indexes) |
| AI | Ollama (`qwen2.5:7b` chat, `nomic-embed-text` embeddings), LangGraph, structured JSON outputs |
| Infra | Redis 7, Docker, Docker Compose, nginx (frontend image) |
| Testing | pytest + FastAPI TestClient, Vitest + React Testing Library |

## AI workflow

The workflow lives in `backend/app/ai/graph.py`:

```mermaid
flowchart TD
    S((START)) --> C[classify_ticket]
    C -->|error| E((END))
    C --> P[determine_priority]
    P -->|error| E
    P --> R[retrieve_knowledge]
    R --> T[retrieve_similar_tickets]
    T --> G[generate_response]
    G -->|error| E
    G --> H[human_review_pause]
    H --> E
```

| Node | What it does | Output |
| --- | --- | --- |
| `classify_ticket` | LLM classifies subject + description into one of 8 categories | `category`, `confidence` |
| `determine_priority` | LLM evaluates outage / payment / security / impact / blocking / dev-only signals | `priority`, `reason`, `confidence` |
| `retrieve_knowledge` | Embeds `subject + description + environment`, pgvector cosine search | top-K chunks with document names |
| `retrieve_similar_tickets` | Same embedding, searched against resolved-ticket embeddings | ticket id, subject, similarity, resolution |
| `generate_response` | LLM drafts a reply using only the retrieved context | `draft_response`, `reasoning_summary`, `confidence`, `requires_more_information`, `requested_information`, `source_references` |
| `human_review_pause` | Marks the draft as awaiting review. **Nothing is sent.** | `awaiting_human_review = true` |

Every LLM call uses Ollama's **structured outputs** (`format` = the Pydantic JSON schema) and is validated
with Pydantic. Malformed output is retried once; after that classification falls back to `OTHER` /
priority to `MEDIUM` (with a visible warning) and response generation fails cleanly so the agent can regenerate.

Anti-hallucination guards (in addition to the prompt rules):
- `source_references` are filtered against the actually retrieved documents/tickets; invented ones are removed and reported as warnings.
- If no documentation and no similar tickets were found, response confidence is capped at 50% and a warning is shown.
- When `requires_more_information` is true the UI lists what to ask for (logs, HTTP status, endpoint, timestamp, browser, environment, recent deployment, config change).

Progress events (`classification_started`, `classification_completed`, `priority_completed`,
`retrieval_completed`, `similar_ticket_search_completed`, `response_generated`) are published to Redis
(in-memory fallback) and streamed to the agent UI over `ws://…/api/ws/tickets/{id}/ai-progress`. If the
WebSocket cannot connect, the UI polls `GET /api/tickets/{id}/ai-analysis` every 2.5 s while the run is active.

## RAG explained

**Ingestion** (`backend/app/services/knowledge_service.py`):

1. Admin uploads a `.txt` or `.md` file (extension, content type, size ≤ 1 MB, UTF-8 and no binary bytes are validated; the filename is sanitised).
2. Text is cleaned (line endings, control characters, excess blank lines).
3. It is split into ~900-character chunks along paragraph boundaries with ~150 characters of word-aligned overlap.
4. Each chunk is embedded locally (`nomic-embed-text`, 768 dims) in batches.
5. Chunks and vectors are stored in `knowledge_chunks.embedding vector(768)` with an HNSW cosine index.

**Retrieval** (`backend/app/ai/retrieval.py`): the ticket's `subject + description + environment` is embedded
and the nearest chunks are selected with `ORDER BY embedding <=> :query LIMIT k`. Results below
`RETRIEVAL_MIN_SIMILARITY` are discarded so unrelated text never reaches the prompt. The chunks are inserted
into the prompt tagged with their document title, which is what the model is allowed to cite.

**Similar tickets** (`backend/app/ai/similar_tickets.py`): when an agent resolves a ticket, a background job embeds
`subject + description + resolution summary` into `ticket_embeddings`. New tickets search that table
(only `RESOLVED`/`CLOSED` tickets, excluding themselves).

## Human in the loop

- The LangGraph flow ends at `human_review_pause`; its result is stored as an `AIResponse` with status `PENDING`
  plus an internal `AI_DRAFT` message that customers can never see.
- The **only** code path that creates a customer-visible message from AI output is
  `ai_service.approve_ai_response`, which requires an authenticated `AGENT` or `ADMIN`.
- Agents can:
  - **Approve** → status `APPROVED`, draft posted as an agent message (marked "AI-assisted, human approved").
  - **Edit** → save changes (`PATCH /ai-response`) and approve → status `EDITED`.
  - **Reject** → status `REJECTED` with an optional reason; nothing is sent.
  - **Regenerate** → re-runs the workflow; the previous pending draft becomes `SUPERSEDED`
    (excluded from acceptance metrics).
- Tests assert that after analysis the customer's view contains no new messages
  (`tests/test_ai.py::test_full_analysis_creates_pending_draft_without_sending`).

## Screenshots

> Placeholder — add your own screenshots after running the app.

| Screen | File |
| --- | --- |
| Agent ticket detail with AI panel | `docs/screenshots/agent-ticket.png` |
| Knowledge base admin | `docs/screenshots/knowledge.png` |
| Analytics | `docs/screenshots/analytics.png` |
| Customer ticket view | `docs/screenshots/customer-ticket.png` |

## Setup requirements

- **Docker Desktop** (or Docker Engine + Compose v2.24+)
- **Ollama** — <https://ollama.com/download> (runs on the host; ~5 GB disk for the models)
- ~8 GB RAM free for `qwen2.5:7b` (use a smaller model such as `qwen2.5:3b` or `llama3.2:3b` on smaller machines)
- For non-Docker development: Python 3.12+, Node.js 20+, PostgreSQL 16 with pgvector, Redis (optional)

## Quick start with Docker

```bash
# 1. Install Docker and Ollama (see links above)

# 2. Pull the required Ollama models (on the host)
ollama pull qwen2.5:7b
ollama pull nomic-embed-text

# 3. Create your environment file
cp .env.example .env            # Windows PowerShell: Copy-Item .env.example .env
#    then set JWT_SECRET_KEY to a long random value

# 4. Build and start frontend, backend, postgres and redis
docker compose up -d --build

# 5. Run database migrations (the backend also runs them automatically on start)
docker compose exec backend alembic upgrade head

# 6. Seed the database (users, tickets, knowledge base, resolved-ticket embeddings)
docker compose exec backend python -m app.scripts.seed

# 7. Open the app
#    Frontend:  http://localhost:5173
#    API docs:  http://localhost:8000/docs
#    Health:    http://localhost:8000/api/health

# 8. Log in with a sample account (see below), e.g. alice@supportdesk.dev / Agent123!
```

Or run everything in one go: `./scripts/setup.sh` (macOS/Linux) or `./scripts/setup.ps1` (Windows PowerShell).

**Port already allocated?** If another PostgreSQL/Redis is already using 5432/6379 (or 8000/5173), change
`POSTGRES_HOST_PORT`, `REDIS_HOST_PORT`, `BACKEND_HOST_PORT` or `FRONTEND_HOST_PORT` in `.env`. Containers talk to each
other on the internal network, so only the host-side port changes.

Useful commands:

```bash
docker compose logs -f backend        # structured JSON logs
docker compose exec backend pytest    # run backend tests inside the container
docker compose down                   # stop
docker compose down -v                # stop and delete the database volume
```

## Ollama setup

The backend talks to Ollama over HTTP; **running Ollama directly on the host is recommended** because GPU
access from Docker differs across machines.

1. Install Ollama and make sure it is running (`ollama serve`, or the desktop app).
2. Pull the models:
   ```bash
   ollama pull qwen2.5:7b          # chat model (OLLAMA_MODEL)
   ollama pull nomic-embed-text    # embedding model (EMBEDDING_MODEL), 768 dimensions
   ```
3. Verify: `curl http://localhost:11434/api/tags` should list both models.

The backend container reaches the host via `http://host.docker.internal:11434` (configured in
`docker-compose.yml`, including the `host-gateway` mapping needed on Linux). On Linux, make Ollama listen on all
interfaces if needed: `OLLAMA_HOST=0.0.0.0 ollama serve`.

**Alternative — Ollama in Docker:**

```bash
docker compose --profile ollama up -d
docker compose exec ollama ollama pull qwen2.5:7b
docker compose exec ollama ollama pull nomic-embed-text
# in .env:  OLLAMA_DOCKER_URL=http://ollama:11434   then: docker compose up -d backend
```

**If Ollama is unavailable** the app keeps working: tickets are still created (the AI status shows as failed
with an explanation), `POST /analyze` returns `503` with `code: "ollama_unavailable"`, and the agent UI shows how
to fix it. Set `EMBEDDING_PROVIDER=hash` to try knowledge search without any model (keyword-level quality).

**Changing models:** set `OLLAMA_MODEL` to any pulled chat model. If you change the embedding model or its
dimension, update `EMBEDDING_DIMENSION`, recreate the database (`docker compose down -v`) and re-seed, because
stored vectors must all come from the same model.

## Local setup without Docker

```bash
# Infrastructure only (or use your own PostgreSQL with pgvector and Redis)
docker compose up -d postgres redis

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
alembic upgrade head                 # reads DATABASE_URL from ../.env
python -m app.scripts.seed
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env                 # VITE_API_URL=http://localhost:8000
npm run dev                          # http://localhost:5173
```

**PostgreSQL setup (manual):** create a database and user, and install pgvector
(<https://github.com/pgvector/pgvector#installation>). The first migration runs
`CREATE EXTENSION IF NOT EXISTS vector`, which requires the extension to be installed on the server.

```sql
CREATE USER support WITH PASSWORD 'support';
CREATE DATABASE support_platform OWNER support;
```

## Environment variables

Defined in `.env.example` (backend reads them via `pydantic-settings`, see `backend/app/core/config.py`).

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://support:support@localhost:5432/support_platform` | SQLAlchemy URL |
| `JWT_SECRET_KEY` | — (≥ 32 chars) | HMAC secret for JWTs. **Set your own.** |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Chat model for classification/priority/drafting |
| `EMBEDDING_PROVIDER` | `ollama` | `ollama` or `hash` |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `EMBEDDING_DIMENSION` | `768` | Vector size (must match model and migration) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis; empty string disables it |
| `FRONTEND_URL` | `http://localhost:5173` | Allowed CORS origin |
| `AI_AUTO_ANALYZE` | `true` | Run the AI workflow when a ticket is created |
| `RAG_TOP_K` / `SIMILAR_TICKETS_TOP_K` | `4` / `3` | Retrieval sizes |
| `RETRIEVAL_MIN_SIMILARITY` | `0.3` | Discard less similar results |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `900` / `150` | Chunking (characters) |
| `MAX_UPLOAD_BYTES` | `1000000` | Knowledge upload limit |
| `RATE_LIMIT_ENABLED` / `AUTH_RATE_LIMIT_PER_MINUTE` | `true` / `20` | Login/register rate limit per IP |
| `VITE_API_URL` | `http://localhost:8000` | Frontend → backend base URL (build-time for Docker) |

## Database and migrations

Models live in `backend/app/models/` (`User`, `Ticket`, `TicketMessage`, `AIResponse`, `AIFeedback`,
`KnowledgeDocument`, `KnowledgeChunk`, `TicketEmbedding`, `TicketEvent`). All relations use foreign keys with
explicit `ON DELETE` behaviour; frequently filtered columns (status, priority, category, assignee, customer,
created_at) are indexed, and both vector columns have HNSW cosine indexes. List endpoints use `selectinload`
to avoid N+1 queries.

Enums are stored as `VARCHAR` (not native PG enums) so adding a value never needs an `ALTER TYPE` migration.

```bash
cd backend
alembic upgrade head                              # apply migrations
alembic downgrade -1                              # roll back one
alembic revision --autogenerate -m "describe change"   # create a new migration after editing models
```

## Seed data and sample accounts

```bash
docker compose exec backend python -m app.scripts.seed          # idempotent
docker compose exec backend python -m app.scripts.seed --reset  # wipe and re-seed
```

The seed creates 1 admin, 2 agents, 3 customers, 10 tickets (5 resolved/closed with resolution summaries,
others open / in progress / waiting), conversation messages, the knowledge documents from `knowledge/`
and embeddings for resolved tickets. Knowledge and ticket embeddings need Ollama; if it was offline, just run the
seed again later — it only adds what is missing.

> ⚠️ **Development-only credentials.** Change or remove these accounts before deploying anywhere.

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@supportdesk.dev` | `Admin123!` |
| Agent | `alice@supportdesk.dev` | `Agent123!` |
| Agent | `bob@supportdesk.dev` | `Agent123!` |
| Customer | `carol@customer.dev` | `Customer123!` |
| Customer | `dave@customer.dev` | `Customer123!` |
| Customer | `erin@customer.dev` | `Customer123!` |

Try this flow: log in as **carol**, create a ticket like *"API key returns 401 in production"*; log in as
**alice**, open it in the queue, watch the AI panel progress, inspect sources and similar tickets, then edit and
approve the draft; log back in as carol to see the reply.

## Running tests

```bash
# Backend (SQLite in-memory + fake LLM, no services required)
cd backend
pytest

# Frontend
cd frontend
npm test            # vitest run
npm run typecheck   # tsc --noEmit
npm run build       # typecheck + production build
```

Backend tests cover registration, login, JWT validation/expiry, role restrictions, ticket creation, customer
isolation, agent access, updates, conversation state changes, assignment, resolution + embedding, AI error
handling (Ollama down, malformed output), approve / edit / reject / regenerate, source filtering, similar ticket
retrieval, feedback, analytics, knowledge upload validation, semantic search and chunking.

Frontend tests cover the login form, protected/role routes, ticket table rendering, the ticket creation form
and the AI response editor.

> The test-suite runs on SQLite, where vector search falls back to Python cosine similarity. The pgvector
> `<=>` path is used whenever the app runs on PostgreSQL.

## API overview

Interactive docs: <http://localhost:8000/docs>. All endpoints are under `/api`; errors return
`{"detail": "...", "code": "..."}`.

| Method | Path | Roles | Description |
| --- | --- | --- | --- |
| POST | `/auth/register` | public | Register a customer, returns JWT |
| POST | `/auth/login` | public | Log in, returns JWT |
| GET | `/auth/me` | any | Current user |
| GET | `/users` | admin | List users (`role`, `search`, `page`, `page_size`) |
| GET | `/users/agents` | staff | Active agents/admins (for assignment) |
| POST | `/tickets` | customer | Create ticket (starts AI analysis in background) |
| GET | `/tickets` | any | List (customers: own only). Filters: `status`, `priority`, `category`, `assigned_agent` (`me`/`unassigned`/id), `search`, `page`, `page_size` |
| GET | `/tickets/{id}` | owner/staff | Detail with conversation (AI drafts hidden from customers) |
| PATCH | `/tickets/{id}` | owner/staff | Staff: status/priority/category/assignee. Customer: close only |
| POST | `/tickets/{id}/messages` | owner/staff | Reply |
| POST | `/tickets/{id}/assign` | staff | Assign to self (admins: any agent) |
| POST | `/tickets/{id}/resolve` | staff | Resolve with `resolution_summary` (indexes for similar search) |
| POST | `/tickets/{id}/analyze` | staff | Start AI analysis (202; 503 if Ollama is down) |
| GET | `/tickets/{id}/ai-analysis` | staff | Status, progress events and latest AI response |
| POST | `/tickets/{id}/ai-response/regenerate` | staff | Re-run the workflow |
| POST | `/tickets/{id}/ai-response/approve` | staff | Approve (optional `edited_response`) and send |
| POST | `/tickets/{id}/ai-response/reject` | staff | Reject with optional `reason` |
| PATCH | `/tickets/{id}/ai-response` | staff | Save an edit to the pending draft |
| POST | `/tickets/{id}/ai-feedback` | staff | Rate a draft 1–5 |
| POST | `/knowledge/documents` | admin | Upload `.md`/`.txt` (multipart `file`) |
| GET | `/knowledge/documents` | staff | List documents |
| GET | `/knowledge/documents/{id}` | staff | Document with chunks |
| DELETE | `/knowledge/documents/{id}` | admin | Delete document and chunks |
| POST | `/knowledge/search` | staff | Semantic search `{query, top_k}` |
| GET | `/analytics/tickets` | staff | Ticket metrics |
| GET | `/analytics/ai` | staff | AI response metrics |
| GET | `/health` | public | DB / Redis / Ollama status |
| WS | `/ws/tickets/{id}/ai-progress?token=JWT` | staff | Live AI progress events |

## Project structure

```
ai-support-engineer-platform/
├── backend/
│   ├── app/
│   │   ├── ai/              # LangGraph workflow, prompts, Ollama client, embeddings, retrieval
│   │   │   ├── graph.py  state.py  prompts.py  ollama_client.py  embeddings.py
│   │   │   ├── classifier.py  priority.py  response_generator.py
│   │   │   ├── retrieval.py  similar_tickets.py  text_processing.py
│   │   ├── api/
│   │   │   ├── deps.py      # auth + role dependencies
│   │   │   ├── router.py
│   │   │   └── routes/      # auth, users, tickets, ai, knowledge, analytics, health, ws
│   │   ├── core/            # config, security (JWT/bcrypt), logging, exceptions, redis, rate limit
│   │   ├── db/              # engine/session, declarative base, column types
│   │   ├── models/          # SQLAlchemy models + enums
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/        # business logic
│   │   ├── scripts/seed.py  # development seed data
│   │   └── main.py          # FastAPI app, middleware, error handlers
│   ├── alembic/             # migrations (0001_initial_schema.py)
│   ├── tests/               # pytest suite
│   ├── Dockerfile  requirements.txt  requirements-dev.txt  alembic.ini
├── frontend/
│   ├── src/
│   │   ├── api/             # Axios client + typed endpoint modules
│   │   ├── components/      # reusable UI (TicketTable, AIAnalysisPanel, AIResponseEditor, …)
│   │   ├── context/         # AuthContext
│   │   ├── hooks/           # TanStack Query hooks, WebSocket progress, debounce
│   │   ├── layouts/         # App and auth layouts
│   │   ├── pages/           # customer/, agent/, admin/, login, register, profile
│   │   ├── routes/          # route table with role guards
│   │   ├── types/           # API types mirroring backend schemas
│   │   ├── utils/           # formatting, errors, roles, token storage
│   │   ├── __tests__/       # Vitest + RTL tests
│   │   ├── App.tsx  main.tsx
│   ├── Dockerfile  nginx.conf  package.json  vite.config.ts  tailwind.config.js
├── knowledge/               # sample docs: authentication, api_keys, billing, troubleshooting
├── scripts/                 # setup.sh / setup.ps1
├── docker-compose.yml
├── .env.example
└── README.md
```

## Known limitations

- **Background jobs** use FastAPI `BackgroundTasks` (in-process). A crash mid-analysis leaves the ticket
  `RUNNING` until it is considered stale after 10 minutes, after which it can be re-run. A Redis-backed queue
  (RQ/Celery/arq) would be the next step.
- **Human review pause** is enforced by the service layer and DB status rather than a LangGraph checkpointer
  interrupt, so the graph does not "resume" after approval; approval is a separate, explicit API action.
- **Tokens** are stored in `localStorage` for simplicity; an httpOnly cookie flow is more resistant to XSS.
  There are no refresh tokens — users log in again when the token expires.
- **Embedding consistency**: all vectors must come from the same embedding model. Changing it requires a
  database reset and re-seed.
- **Local model quality** depends on the model you run; 7B models occasionally misclassify or return
  low-confidence drafts, which is exactly why human review is mandatory.
- Admin user management is read-only (no UI to create staff or deactivate users yet).
- Only `.md` and `.txt` uploads are supported (no PDF/HTML extraction).

## Future improvements

- Redis-backed job queue with retries and a worker container
- LangGraph checkpointer (Postgres) with true `interrupt` / resume semantics
- Streaming token output for drafts; reranking of retrieved chunks
- Admin CRUD for users, SLAs, canned responses, ticket attachments, email notifications
- Evaluation harness: offline dataset of tickets to measure classification accuracy and draft acceptance
- OpenTelemetry tracing and Prometheus metrics
- Refresh tokens / cookie-based auth, per-user rate limits

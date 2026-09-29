You are a senior full-stack software engineer and AI engineer.

Build the ENTIRE project described below in the current repository.

Do not stop after planning.
Do not only give architecture.
Do not wait for confirmation between phases.

Create all required folders, files, code, configuration, database models, frontend pages, backend APIs, AI workflow, Docker setup, tests, and README needed to run the project locally.

The final result must be a complete portfolio-quality application that I can run, inspect, learn from, and improve later.

I want the entire project generated now.

# PROJECT NAME

AI Support Engineer Platform

# PROJECT PURPOSE

Build a production-style full-stack customer support platform with AI assistance.

The application should work like a simplified combination of Zendesk/Intercom plus an AI support assistant.

Customers submit support tickets.

Support engineers manage tickets.

AI automatically:

- classifies tickets
- assigns priority
- searches support documentation
- retrieves similar solved tickets
- generates a suggested response
- provides evidence/sources
- pauses for human approval

The AI must NEVER automatically send a response to a customer.

A human support agent must approve, edit, reject, or regenerate the response.

# IMPORTANT CONSTRAINT: EVERYTHING MUST BE FREE

Do not use paid APIs.

Do not use:

- OpenAI API
- Anthropic API
- Gemini API
- Pinecone
- paid cloud services
- paid databases

Use only free/open-source/local technologies.

AI inference must use Ollama locally.

# TECHNOLOGY STACK

Frontend:

- React
- TypeScript
- Vite
- Tailwind CSS
- React Router
- TanStack Query
- Axios

Backend:

- Python
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic

Database:

- PostgreSQL
- pgvector

AI:

- Ollama
- LangGraph
- local embeddings
- RAG
- structured outputs
- semantic search
- human-in-the-loop

Supporting infrastructure:

- Redis
- Docker
- Docker Compose

Testing:

- pytest
- FastAPI TestClient
- React Testing Library

# HIGH-LEVEL ARCHITECTURE

Use this architecture:

React + TypeScript
        |
        | REST API
        |
FastAPI
        |
        |------ PostgreSQL
        |          |
        |          |------ pgvector
        |
        |------ Redis
        |
        |------ LangGraph
                    |
                    |------ Ollama
                    |
                    |------ RAG
                    |
                    |------ Similar Ticket Search

Frontend and backend must be separate applications.

Do not mix business logic into route files.

Use service layers.

Keep AI code in its own module.

# REQUIRED USER ROLES

Support these roles:

CUSTOMER
AGENT
ADMIN

# CUSTOMER FEATURES

Customers must be able to:

- register
- login
- logout
- view own profile
- create support ticket
- view own tickets
- open ticket detail
- reply to ticket
- see ticket status
- see agent responses
- close ticket if appropriate

Customers must NEVER see another customer's ticket.

# SUPPORT AGENT FEATURES

Agents must be able to:

- login
- view all open tickets
- filter tickets
- search tickets
- view ticket details
- assign tickets to themselves
- change ticket status
- see AI classification
- see AI priority
- see AI confidence
- see AI-generated draft
- see retrieved documentation
- see similar resolved tickets
- approve AI draft
- edit AI draft
- reject AI draft
- regenerate AI draft
- manually reply
- resolve ticket

# ADMIN FEATURES

Admins must be able to:

- login
- view users
- view agents
- view customers
- manage knowledge base
- upload .txt and .md files
- delete documents
- view analytics
- see AI response acceptance metrics
- see ticket metrics

# AUTHENTICATION

Use JWT authentication.

Implement:

POST /api/auth/register
POST /api/auth/login
GET /api/auth/me

Requirements:

- hash passwords securely
- never store plain passwords
- validate JWT
- protect endpoints by role
- use environment variables for JWT secret

# DATABASE MODELS

Create these SQLAlchemy models.

## User

Fields:

id
name
email
password_hash
role
is_active
created_at
updated_at

## Ticket

Fields:

id
customer_id
assigned_agent_id
subject
description
environment
category
priority
status
ai_confidence
created_at
updated_at
resolved_at

Statuses:

OPEN
IN_PROGRESS
WAITING_FOR_CUSTOMER
RESOLVED
CLOSED

Priorities:

LOW
MEDIUM
HIGH
CRITICAL

Categories:

AUTHENTICATION
BILLING
ACCOUNT
API
PERFORMANCE
BUG
FEATURE_REQUEST
OTHER

## TicketMessage

Fields:

id
ticket_id
sender_id
message
message_type
created_at

Types:

CUSTOMER
AGENT
AI_DRAFT
SYSTEM

## AIResponse

Fields:

id
ticket_id
generated_response
reasoning_summary
confidence_score
status
approved_by
edited_response
created_at
updated_at

Status:

PENDING
APPROVED
EDITED
REJECTED

## AIFeedback

Fields:

id
ai_response_id
agent_id
rating
comments
created_at

## KnowledgeDocument

Fields:

id
title
filename
content_type
created_at
updated_at

## KnowledgeChunk

Fields:

id
document_id
content
embedding
chunk_index
created_at

Use pgvector for embedding.

## TicketEmbedding

Fields:

id
ticket_id
embedding
resolution_summary
created_at

Use it for similar solved ticket search.

## TicketEvent

Fields:

id
ticket_id
event_type
metadata
created_at

Examples:

TICKET_CREATED
AI_ANALYSIS_STARTED
AI_ANALYSIS_COMPLETED
AGENT_ASSIGNED
AI_RESPONSE_APPROVED
AI_RESPONSE_REJECTED
TICKET_RESOLVED

# DATABASE REQUIREMENTS

Use PostgreSQL.

Use Alembic for migrations.

Add indexes where appropriate.

Add relationships correctly.

Use foreign keys.

Avoid N+1 query problems where reasonable.

# FRONTEND ROUTES

Create these pages.

Public:

/login
/register

Customer:

/customer/dashboard
/customer/tickets
/customer/tickets/new
/customer/tickets/:id

Agent:

/agent/dashboard
/agent/tickets
/agent/tickets/:id

Admin:

/admin/dashboard
/admin/users
/admin/knowledge
/admin/analytics

# FRONTEND UI

Create a clean modern developer-tool style interface.

Use Tailwind CSS.

Design should be simple and professional.

Create reusable components:

Navbar
Sidebar
ProtectedRoute
RoleProtectedRoute
TicketCard
TicketTable
TicketFilters
TicketSearch
TicketStatusBadge
PriorityBadge
CategoryBadge
ConversationMessage
AIAnalysisPanel
AIResponseEditor
SimilarTicketsPanel
KnowledgeSourcesPanel
AnalyticsCard
LoadingSpinner
ErrorMessage
Modal
Pagination

# FRONTEND STATE

Use:

- TanStack Query for server data
- React Context for auth
- local component state for UI state

Do NOT use Redux unless necessary.

# API CLIENT

Create a reusable Axios client.

It should:

- use backend base URL from environment variable
- automatically attach JWT token
- handle unauthorized responses

# BACKEND API

Implement these endpoints.

## Auth

POST /api/auth/register
POST /api/auth/login
GET /api/auth/me

## Tickets

POST /api/tickets
GET /api/tickets
GET /api/tickets/{ticket_id}
PATCH /api/tickets/{ticket_id}
POST /api/tickets/{ticket_id}/messages
POST /api/tickets/{ticket_id}/assign
POST /api/tickets/{ticket_id}/resolve

## AI

POST /api/tickets/{ticket_id}/analyze
GET /api/tickets/{ticket_id}/ai-analysis
POST /api/tickets/{ticket_id}/ai-response/regenerate
POST /api/tickets/{ticket_id}/ai-response/approve
POST /api/tickets/{ticket_id}/ai-response/reject
PATCH /api/tickets/{ticket_id}/ai-response
POST /api/tickets/{ticket_id}/ai-feedback

## Knowledge

POST /api/knowledge/documents
GET /api/knowledge/documents
GET /api/knowledge/documents/{document_id}
DELETE /api/knowledge/documents/{document_id}
POST /api/knowledge/search

## Analytics

GET /api/analytics/tickets
GET /api/analytics/ai

# PAGINATION / FILTERS

GET /api/tickets should support:

- status
- priority
- category
- assigned_agent
- search
- page
- page_size

# AI MODULE STRUCTURE

Create:

backend/app/ai/

Suggested files:

state.py
graph.py
ollama_client.py
classifier.py
priority.py
retrieval.py
similar_tickets.py
response_generator.py
embeddings.py
prompts.py

# OLLAMA

Use Ollama locally.

Use environment variable:

OLLAMA_MODEL

Default to a reasonable free local model such as:

qwen2.5:7b

But make model configurable.

If Ollama is unavailable:

- backend should not crash
- return a clear error
- UI should display helpful message

# EMBEDDINGS

Use local embeddings.

Prefer:

nomic-embed-text through Ollama

or Sentence Transformers if easier.

Make embedding provider configurable.

Do not use paid embedding APIs.

# KNOWLEDGE BASE INGESTION

Admin uploads .txt or .md document.

Pipeline:

upload document
    |
extract text
    |
clean text
    |
split into chunks
    |
generate embeddings
    |
store in pgvector

Chunking should use reasonable overlap.

Store:

document id
chunk index
content
embedding

# RAG SEARCH

For new ticket:

combine:

subject + description + environment

Generate embedding.

Search knowledge chunks using vector similarity.

Return top K chunks.

Use retrieved chunks in AI response prompt.

Include source document names.

Do not invent sources.

# SIMILAR TICKET SEARCH

When a ticket is resolved:

generate an embedding from:

subject
description
final resolution

Store it.

For new ticket:

generate embedding
search resolved tickets
return top similar tickets

Show:

ticket ID
subject
similarity
resolution summary

# LANGGRAPH WORKFLOW

Create this workflow:

START
  |
classify_ticket
  |
determine_priority
  |
retrieve_knowledge
  |
retrieve_similar_tickets
  |
generate_response
  |
human_review_pause

Graph state should include:

ticket_id
subject
description
environment
category
priority
classification_confidence
priority_reason
knowledge_results
similar_tickets
draft_response
reasoning_summary
response_confidence
requires_more_information
error

# CLASSIFICATION NODE

Input:

subject
description

Return structured JSON:

category
confidence

# PRIORITY NODE

Evaluate:

- production outage
- payment failure
- security issue
- widespread impact
- blocking issue
- development-only issue

Return:

priority
reason
confidence

# RETRIEVAL NODE

Search pgvector.

Return top knowledge chunks.

# SIMILAR TICKET NODE

Return top similar solved tickets.

# RESPONSE GENERATOR

Use:

ticket context
retrieved knowledge
similar tickets

Generate structured response:

draft_response
reasoning_summary
confidence
requires_more_information
requested_information
source_references

# IMPORTANT AI BEHAVIOR

AI must not hallucinate unsupported facts.

If information is insufficient:

set:

requires_more_information = true

and suggest information to request.

Possible information:

- logs
- HTTP status
- API endpoint
- timestamp
- browser
- environment
- recent deployment
- configuration change

# HUMAN IN THE LOOP

The LangGraph flow must stop after response generation.

A support agent must explicitly:

approve
edit
reject
or regenerate

Only approved or edited responses can be added to customer conversation.

AI must NEVER autonomously send customer-facing messages.

# REDIS

Use Redis for:

- caching
- background processing support
- rate limiting preparation

Keep implementation simple.

If Redis is unavailable during development, fail gracefully where possible.

# BACKGROUND AI PROCESSING

AI analysis should not block normal application usage unnecessarily.

Use a simple background job approach.

If Celery adds too much complexity, use FastAPI BackgroundTasks first.

Keep Redis integrated and ready for future queue work.

# WEBSOCKET OR POLLING

Implement live AI progress if reasonable.

Preferred:

WebSockets

Events:

classification_started
classification_completed
priority_completed
retrieval_completed
similar_ticket_search_completed
response_generated

If WebSockets make project unstable, implement polling cleanly instead.

# ANALYTICS

Agent/admin dashboard should calculate real metrics from database:

- total tickets
- open tickets
- critical tickets
- resolved tickets
- tickets by category
- tickets by priority
- average resolution time
- AI response approval count
- AI rejection count
- AI edit count
- AI approval rate

Do not create fake metrics.

# ERROR HANDLING

Handle:

- invalid login
- expired JWT
- unauthorized access
- invalid ticket
- Ollama unavailable
- malformed AI output
- database failure
- embedding failure
- document upload failure
- vector search failure

Frontend should show useful error messages.

# LOGGING

Use structured backend logging.

Include when relevant:

request_id
user_id
ticket_id
operation
latency_ms
success
error

Never log:

passwords
JWTs
secrets

# SECURITY

Implement:

- password hashing
- JWT
- RBAC
- input validation
- environment secrets
- CORS
- safe file upload validation
- basic rate limiting if reasonable

Do not commit secrets.

# ENVIRONMENT FILES

Create:

.env.example

Include:

DATABASE_URL
JWT_SECRET_KEY
JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES
OLLAMA_BASE_URL
OLLAMA_MODEL
REDIS_URL
FRONTEND_URL

Frontend:

VITE_API_URL

# DOCKER

Create Dockerfiles for frontend and backend.

Create docker-compose.yml for:

frontend
backend
postgres
redis

Provide clear Ollama setup instructions.

If running Ollama inside Docker is unnecessarily difficult across machines, document running Ollama directly on host.

# SEED DATA

Create a seed script.

Create:

1 admin
2 agents
3 customers
sample tickets
sample ticket messages
sample resolved tickets

Use obvious development-only passwords and clearly document them in README.

Also create sample knowledge files such as:

knowledge/authentication.md
knowledge/api_keys.md
knowledge/billing.md
knowledge/troubleshooting.md

# TESTING

Backend tests:

- registration
- login
- JWT auth
- role restrictions
- create ticket
- customer ticket isolation
- agent ticket access
- ticket update
- AI endpoint error handling
- approve AI response
- reject AI response
- knowledge upload
- search

Frontend tests:

- login form
- protected routes
- ticket list rendering
- ticket creation form
- AI response editor

# CODE QUALITY

Follow these rules:

- readable code
- proper typing
- descriptive names
- modular architecture
- no giant files
- no unnecessary abstractions
- no premature microservices
- comments only when useful
- consistent formatting
- remove dead code
- no placeholder TODOs for core features

# REQUIRED FOLDER STRUCTURE

Create approximately:

ai-support-engineer-platform/

frontend/
    src/
        api/
        components/
        context/
        hooks/
        layouts/
        pages/
        routes/
        types/
        utils/
        App.tsx
        main.tsx

backend/
    app/
        api/
            routes/
        ai/
        core/
        db/
        models/
        schemas/
        services/
        main.py

    tests/
    alembic/

knowledge/

scripts/

docker-compose.yml

.env.example

README.md

# README

Write a complete professional README.

Include:

- project overview
- problem being solved
- features
- architecture
- technology stack
- AI workflow
- RAG explanation
- human-in-the-loop explanation
- screenshots placeholder section
- setup requirements
- local setup
- Docker setup
- Ollama setup
- required Ollama models
- PostgreSQL setup
- environment variables
- database migration commands
- seed commands
- frontend commands
- backend commands
- test commands
- sample accounts
- API overview
- project structure
- future improvements

Include Mermaid architecture diagram.

# REQUIRED LOCAL SETUP

The final project should support a workflow similar to:

1. install Docker
2. install Ollama
3. pull required Ollama models
4. copy .env.example to .env
5. run docker compose up
6. run migrations
7. seed database
8. open frontend
9. login using sample account

Document exact commands.

# IMPORTANT

Do not merely describe files.

Actually CREATE them in the repository.

Do not stop after writing README.

Do not leave core features as pseudocode.

Do not ask me to manually create files that you can create.

If something is too complex to implement perfectly, implement the simplest working version and document the limitation.

Prioritize having a complete runnable project.

# FINAL VALIDATION

Before finishing:

1. inspect project structure
2. verify imports
3. verify backend routes
4. verify React routes
5. verify environment variable names
6. verify Docker configuration
7. verify database model relationships
8. verify migrations
9. verify seed script
10. verify API/client paths
11. verify Ollama integration
12. verify pgvector usage
13. verify LangGraph flow
14. verify role-based authorization
15. verify customer ticket isolation
16. verify AI cannot send responses without approval
17. verify README setup instructions

Fix obvious inconsistencies before you finish.

At the very end, give me:

- what was created
- how to run it
- sample login credentials
- which Ollama models to pull
- any known limitations
- recommended files to study first

Start building the complete project now.
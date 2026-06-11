# Ivory Implementation Spec

## Summary

This document is the execution-ready build spec for the Ivory Insurance Assistant. It complements the existing root docs and remains a reference for how the current implementation is expected to behave.

## Project Status

### Current state

The repository now contains a working implementation:
- `backend/` FastAPI + LangGraph application
- `frontend/` Next.js App Router UI
- `tests/` backend integration coverage
- `docker-compose.backend.yml` and backend container files
- knowledge-base content, ingestion, and local vector store support

### Role of this document

This file is now a behavior and architecture reference. If there is any ambiguity, the live code in `backend/` and `frontend/` is the source of truth.

## Environment Setup

### Required versions

- Python 3.11+
- Node.js 18+
- npm 9+

### Canonical Python setup

All Python work must happen inside a local virtual environment located at:

`backend/.venv`

Required setup flow:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Unix/macOS equivalent:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Environment rules

- `.venv` is the Python runtime environment
- `.env` is configuration only
- Python packages must not be installed globally
- all backend commands, tests, and ingestion scripts must run with the active `backend/.venv`
- `.venv/` and `.env` must remain gitignored

## Product Goal

Build an AI-powered insurance assistant that can both:
- answer insurance product questions using retrieval-augmented generation
- guide a user through a structured quote-generation flow for auto, home, and life insurance

### Non-goals for v1

- production-grade actuarial pricing
- enterprise auth and role-based access control
- multi-tenant SaaS architecture
- advanced analytics dashboard

## Target System

### Final architecture

- **Backend:** FastAPI application in Python
- **Workflow orchestration:** LangGraph state machine
- **LLM access:** OpenRouter through a dedicated client wrapper
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2`
- **Vector store:** local persistent ChromaDB
- **Frontend:** Next.js App Router + React + TypeScript + Tailwind CSS
- **Streaming:** SSE over `POST /chat`
- **Runtime:** local dev first, Docker-friendly structure second

### Operating modes

- `conversational`
  Answers product and policy questions with RAG

- `transactional`
  Collects quote inputs, validates them, calculates a quote, and confirms next action

## Functional Requirements

### Conversational RAG

- answer policy/product questions using retrieved company knowledge base content
- prefer grounded answers over generic model responses
- degrade gracefully if retrieval returns nothing

### Quote workflow

- support `auto`, `home`, and `life` quote flows
- identify product type if the user asks for a quote without naming one
- collect required fields one step at a time
- validate values and re-prompt only for invalid fields
- calculate a deterministic quote result
- allow accept, adjust, and restart behavior

### Mid-flow switching

- if a user asks a product question during quote collection, answer it without losing current workflow state
- after answering, return to the prior quote step with preserved `insurance_type`, `quote_step`, and `collected_data`

### Session behavior

- allow multiple turns in one session
- support sequential quotes in one session
- support explicit reset for a single session

## System Design

### Canonical state

```python
class ChatState(TypedDict):
    session_id: str
    messages: list
    mode: str
    intent: str
    quote_step: str
    insurance_type: str | None
    collected_data: dict
    quote_result: dict | None
    pending_question: str | None
    last_error: str | None
    trace_id: str | None
```

### Intent model

The system must classify every user message into exactly one of:
- `question`
- `quote`
- `response`

`response` is mandatory so that structured answers like `"2019 Toyota Camry"` are treated as form responses instead of fresh top-level intents.

### Modes and steps

- `mode`
  - `conversational`
  - `transactional`

- `quote_step`
  - `identify`
  - `collect`
  - `validate`
  - `confirm`

### Graph nodes

- `router`
  - classify user intent
  - choose RAG or transactional branch

- `rag_answer`
  - retrieve relevant docs
  - generate grounded answer
  - return to prior workflow state if the session was transactional

- `identify_product`
  - infer or confirm insurance type

- `collect_details`
  - request required fields for the chosen product
  - merge valid responses into `collected_data`

- `validate_quote`
  - validate current data
  - compute quote result if complete and valid

- `confirm`
  - present quote result
  - handle accept, adjust, or restart

### Failure handling

- OpenRouter failure: return a controlled fallback or error response without breaking the quote workflow
- empty retrieval: answer conservatively and indicate missing knowledge
- invalid user input: re-ask only the affected field
- state corruption: reset the session and return a recovery message
- unclassifiable input: default to conversational handling unless the session is clearly mid-transaction

## Interfaces

### Backend endpoints

#### `POST /chat`

Request body:

```json
{
  "message": "I want an auto quote",
  "session_id": "abc123"
}
```

Response:
- `Content-Type: text/event-stream`

Required SSE events:
- `token`
  incremental content chunks
- `message_complete`
  final assembled assistant message and any structured payload
- `error`
  controlled error event with user-safe message

Optional SSE events:
- `state`
  lightweight debug/progress event for development mode

#### `POST /reset`

Request body:

```json
{
  "session_id": "abc123"
}
```

Behavior:
- clears only the targeted session state

#### `GET /health`

Behavior:
- returns simple readiness status for local/dev checks

### Environment contract

`env.example` must define placeholders only:

```env
OPENROUTER_API_KEY=
# OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
# CHROMA_PERSIST_DIR=./vectorstore
```

Required config:
- `OPENROUTER_API_KEY`

Optional config:
- `OPENROUTER_MODEL`
- `CHROMA_PERSIST_DIR`

## Implementation Workstreams

### Workstream A: Backend Core

Scope:
- FastAPI app
- LangGraph state and graph definition
- router and transactional nodes
- quote calculator service
- session store boundary

Outputs:
- runnable backend API
- deterministic quote flow behavior
- local session handling

Done criteria:
- `/chat`, `/reset`, and `/health` work locally
- transaction flow works for all three insurance types

### Workstream B: RAG Services

Scope:
- knowledge base structure
- document ingestion
- embedding pipeline
- ChromaDB setup
- retrieval logic
- LLM answer assembly

Outputs:
- reproducible ingestion flow
- grounded answers for insurance docs

Done criteria:
- ingestion works from source docs
- Q&A returns retrieved, grounded responses

### Workstream C: Frontend

Scope:
- React app shell
- chat window and message rendering
- SSE hook
- typing/loading states
- quote card rendering
- reset/start-over controls

Outputs:
- local web UI connected to backend

Done criteria:
- streamed responses render progressively
- quote interactions are usable end-to-end

### Workstream D: Quality And Infra

Scope:
- test scenarios
- fixture conversations
- structured logging and trace IDs
- environment hygiene
- rate-limit scaffolding

Outputs:
- repeatable validation checks
- basic observability
- safer local setup

Done criteria:
- key flows are testable locally
- logs and trace IDs exist for requests

## Execution Order

### Phase 1

- scaffold backend structure
- create `backend/.venv`
- define `ChatState`
- implement API skeleton and session handling boundary

### Phase 2

- implement router, identify, collect, validate, confirm nodes
- implement quote calculator
- make transactional flow work without RAG

### Phase 3

- implement knowledge base ingestion
- implement ChromaDB retrieval
- implement `rag_answer`
- wire mid-flow switching behavior

### Phase 4

- build frontend chat UI
- connect SSE streaming
- render quote summaries

### Phase 5

- add logging, trace IDs, reset handling, tests, and rate-limit scaffolding
- document setup and local run flow

### Parallelization rules

- Workstream B can begin after backend contracts and document format are defined
- Workstream C can begin after `/chat` SSE contract and request shapes are locked
- Workstream D can begin as soon as endpoint contracts and state model are stable

## Agent-Ready Ownership

### Subagent 1: Backend Core

Owns:
- graph
- state
- API wiring
- quote flow nodes
- quote calculator
- backend virtual environment bootstrap docs

### Subagent 2: RAG Services

Owns:
- knowledge base format
- embeddings
- ChromaDB
- ingestion
- retrieval
- grounded answer assembly

### Subagent 3: Frontend

Owns:
- UI shell
- SSE client hook
- chat rendering
- quote cards
- reset UX

### Subagent 4: Quality/Infra

Owns:
- test scenarios
- fixture conversations
- log/trace standards
- `.env` and `.venv` hygiene
- rate-limit scaffolding

### Shared contracts

All agents must honor:
- the `ChatState` shape
- endpoint shapes
- SSE event names
- `session_id`-scoped behavior
- deterministic quote calculation outside the LLM

## Acceptance Criteria

- backend can be installed and run from `backend/.venv`
- product Q&A works from retrieved knowledge base content
- auto, home, and life quote flows complete successfully
- mid-flow question switching preserves transactional progress
- invalid inputs trigger targeted re-prompts
- quote accept, adjust, and restart behaviors work
- reset clears only one session
- SSE streams progressively and closes cleanly
- logs include request/trace information
- the app can be run locally by following the documented setup

## Test Scenarios

1. Create `backend/.venv` and install backend dependencies successfully.
2. Ask a general insurance question and receive a grounded answer.
3. Start an auto quote and complete it successfully.
4. Start a home quote and complete it successfully.
5. Start a life quote and complete it successfully.
6. Ask a product question during quote collection and resume correctly.
7. Submit invalid data and confirm only the bad field is re-requested.
8. Restart after a quote and begin a new quote in the same session.
9. Trigger retrieval with an empty store and verify graceful fallback.
10. Simulate OpenRouter failure and verify controlled fallback or user-facing recovery.
11. Confirm `POST /reset` clears only the targeted session.

## Risks And Defaults

### Defaults chosen

- use local persistent ChromaDB instead of managed vector infrastructure
- use in-memory session state first, behind a replaceable persistence boundary
- use deterministic quote logic in service code
- use OpenRouter model selection through env vars
- use structured logging and trace IDs in the initial build

### Known risks

- LLM intent classification can drift without eval coverage
- RAG quality depends on document quality and chunking
- SSE behavior varies slightly across browser/runtime integrations
- session persistence will need a durable backend for multi-instance deployment

### Follow-up improvements after v1

- Redis or Postgres session persistence
- LangSmith or equivalent tracing
- richer eval suite in CI
- better prompt/version management
- stronger rate limiting and abuse controls

<div align="center">

<img src="assets/brand/ivory-icon.svg" alt="Ivory app icon" width="96"/>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/brand/ivory-wordmark-dark.svg">
  <img src="assets/brand/ivory-wordmark.svg" alt="Ivory" width="280"/>
</picture>

**The front desk that never sleeps.**

Ivory answers patient questions, captures every lead, and books the appointment —
while your team stays chairside.

</div>

---

## What is Ivory?

Ivory is an AI front-desk / lead-intake agent built on a pattern designed for
correctness, not vibes:

> **Deterministic Orchestrator + RAG + Stateful Slot-Filling** — a state machine
> drives control flow, the LLM only generates answer text, and a LangGraph
> checkpointer gives the session durable memory.

Two coordinated behaviors live in one session:

- **Conversational RAG** for knowledge questions, answered from a curated corpus
- **Deterministic intake flows** that collect required fields step by step with
  field-level validation — and survive interruptions

A patient can start booking, interrupt with a question, get an answer, and resume
at the exact pending field. The backend is the single source of truth for both
chat state and intake state.

## Project Status

This codebase started as **ShieldBase**, an insurance-assistant take-home, and is
being rebranded into Ivory for the dental vertical. Same architecture, new skin
and corpus.

| Piece | Status |
|-------|--------|
| Deterministic state machine, RAG, slot-filling, durable memory | ✅ Built and tested (41 green) |
| Brand + design system | ✅ `docs/branding/IVORY_BRAND.md`, `design-system/ivory/MASTER.md` |
| Current running vertical | Insurance quotes (`auto`, `home`, `life`) — the ShieldBase heritage |
| Dental vertical (NIDCR/CDC corpus, Cal.com booking, Airtable CRM, Resend email) | 🔜 In progress — research locked in `docs/DATASET_RESEARCH_DENTAL.md` |

## Chat Modes

### Conversational mode

Used for knowledge questions. The backend retrieves knowledge-base chunks,
generates an answer, and streams it back to the UI over SSE.

### Transactional mode

Used for intake flows. The backend identifies the product/service, collects
required fields, validates them, computes a deterministic result, and moves the
user into confirmation.

The system is explicitly designed to move between these two modes without
dropping session state.

## The Deterministic Flow

```text
identify -> collect details -> validate -> confirm
```

Behaviors the state machine guarantees:

- explicit flow-start messages are routed into the transactional branch
- bare field replies like `2019` stay in the transactional branch instead of drifting into RAG
- compact inputs like `Toyota, Camry, 35, 0, standard` can fill multiple fields in sequence
- a knowledge question mid-flow gets answered, then the exact resume prompt for the pending field is appended
- `accept`, `adjust`, and `restart` are supported after a result is generated
- invalid input never advances the flow step

## Stack

| Component | Technology |
|-----------|-----------|
| Backend orchestration | Python + LangGraph `StateGraph` |
| API layer | FastAPI + Server-Sent Events |
| LLM | OpenRouter |
| Retrieval | ChromaDB + sentence-transformers |
| Frontend | Next.js App Router + React + Tailwind CSS |
| Business logic | Deterministic Python (never LLM-generated) |
| Session persistence | In-memory with Redis support |

## High-Level Request Path

```text
Browser -> Next.js UI -> /api/chat proxy -> FastAPI /chat
                                           |
                                           v
                                  LangGraph state machine
                                           |
                     +---------------------+----------------------+
                     |                                            |
                     v                                            v
                  RAG path                              transactional workflow
         retrieve -> answer -> stream               identify -> collect -> validate -> confirm
```

## Project Structure

```text
.
├── backend/
│   ├── main.py
│   ├── graph.py
│   ├── state.py
│   ├── nodes/
│   ├── services/
│   ├── knowledge_base/
│   └── requirements.txt
├── frontend/
│   ├── app/
│   ├── src/
│   └── package.json
├── assets/brand/          # Ivory logo SVGs
├── design-system/ivory/   # design tokens + component specs
├── docs/
└── tests/
```

## Local Run

### Backend

```bash
cd backend
source .venv/bin/activate
python -m uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000`.

## Validation

Backend integration coverage includes:

- health and reset endpoints
- all three intake flows end to end
- interruption and resume behavior
- invalid input re-prompts
- product switching mid-flow
- `adjust` and `restart`
- protection against LLM misclassification of flow-start and field replies
- compact multi-field input handling

Run the backend test suite from the repo root:

```bash
python -m pytest tests/test_backend_integration.py -q
```

## Key Invariants

- backend state is the source of truth
- business results are deterministic, not LLM-generated
- invalid field input must not advance the flow step
- mid-flow knowledge questions must not clear `collected_data`
- flow-start intents must not be downgraded into generic RAG
- the frontend renders backend state; it never invents flow state on its own

## Brand & Design

- [Brand guide](docs/branding/IVORY_BRAND.md) — name, voice, taglines, logo rules
- [Design system](design-system/ivory/MASTER.md) — tokens, components, checklists
- Logo assets in [`assets/brand/`](assets/brand/)

## Useful Docs

- [Engineering walkthrough](docs/ENGINEERING_WALKTHROUGH.md)
- [Quote flow test checklist](docs/guides/QUOTE_FLOW_TEST_CHECKLIST.md)
- [ASCII architecture](docs/architecture/ASCII_ARCHITECTURE.md)
- [Architecture decisions](docs/architecture/ARCHITECTURE_DECISIONS.md)
- [Plain-English overview](docs/layman/OVERVIEW_IN_PLAIN_ENGLISH.md)
- [Local run guide](docs/guides/LOCAL_RUN_INSTRUCTIONS.md)
- [Dental dataset research](docs/DATASET_RESEARCH_DENTAL.md)

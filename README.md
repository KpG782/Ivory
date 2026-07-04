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

Ivory is an AI front-desk / lead-intake agent for a dental clinic, built on a
pattern designed for correctness, not vibes:

> **Deterministic Orchestrator + RAG + Stateful Slot-Filling** — a state machine
> drives control flow, the LLM only generates answer text, and a LangGraph
> checkpointer gives the session durable memory.

Two coordinated behaviors live in one session:

- **Conversational RAG** for oral-health and clinic questions, answered from a
  curated public-domain corpus (NIDCR + CDC) plus clinic docs
- **Deterministic intake flows** that collect required fields step by step with
  field-level validation — and survive interruptions

A patient can start booking a cleaning, interrupt with "what does a checkup
include?", get an answer, and resume at the exact pending field. The backend is
the single source of truth for both chat state and intake state.

## Project Status

| Piece | Status |
|-------|--------|
| Deterministic state machine, RAG, slot-filling, durable memory | ✅ Built and tested (56 green) |
| Dental vertical: services, visit estimator, NIDCR/CDC corpus | ✅ Live (`docs/specs/DENTAL_VERTICAL_SPEC.md`) |
| Front-desk integrations: Airtable CRM, Cal.com booking, Resend email | ✅ Built with offline dry-run mode (no keys required for demo) |
| Brand + design system | ✅ `docs/branding/IVORY_BRAND.md`, `design-system/ivory/MASTER.md` |

The codebase started as an insurance-assistant take-home; the dental conversion
kept the architecture and replaced the vertical (research and licensing
decisions in `docs/DATASET_RESEARCH_DENTAL.md` — public-domain sources only,
never ADA content).

## Services

| Service | Slots collected | Deterministic result |
|---------|-----------------|----------------------|
| `cleaning` — routine exam & cleaning | name, email, last visit year, insurance status, preferred time | visit-cost estimate range |
| `emergency` — urgent visit | name, phone, issue type, pain level (0–10), insurance status | visit-cost estimate range |
| `cosmetic` — consultation | name, email, treatment, budget band, timeline | treatment estimate range |

Estimates come from a deterministic fee schedule
(`backend/services/visit_estimator.py`) — never from the LLM — and always carry
an "educational estimate, not a diagnosis or final price" disclaimer.

## The Deterministic Flow

```text
identify -> collect details -> validate -> confirm
```

Behaviors the state machine guarantees:

- explicit booking messages are routed into the transactional branch
- bare field replies like `2024` stay in the transactional branch instead of drifting into RAG
- compact inputs like `Maria Santos, maria@example.com, 2024, insured, morning` can fill multiple fields in sequence
- an oral-health question mid-flow gets answered, then the exact resume prompt for the pending field is appended
- `accept`, `adjust`, and `restart` are supported after an estimate is generated
- invalid input never advances the flow step

On `accept`, the deterministic front-desk layer fires three integrations —
Airtable (lead), Cal.com (booking request), Resend (email confirmation) — and
reports each outcome in chat. With no API keys configured, every integration
runs in **dry-run mode**: no network I/O, deterministic demo output.

## Stack

| Component | Technology |
|-----------|-----------|
| Backend orchestration | Python + LangGraph `StateGraph` |
| API layer | FastAPI + Server-Sent Events |
| LLM | OpenRouter |
| Retrieval | ChromaDB + sentence-transformers |
| Frontend | Next.js App Router + React + Tailwind CSS |
| Business logic | Deterministic Python (never LLM-generated) |
| CRM / booking / email | Airtable + Cal.com + Resend (stdlib HTTP clients, dry-run without keys) |
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
                  RAG path                              transactional intake
         retrieve -> answer -> stream               identify -> collect -> validate -> confirm
                                                                                        |
                                                                              accept -> front desk
                                                                          Airtable + Cal.com + Resend
```

## Project Structure

```text
.
├── backend/
│   ├── main.py
│   ├── graph.py
│   ├── state.py
│   ├── nodes/               # router, identify_service, collect_details,
│   │                        # validate_visit, confirm, rag
│   ├── services/            # visit_estimator, front_desk, airtable,
│   │                        # calcom, resend_email, llm, vectorstore
│   ├── knowledge_base/      # 12 dental docs (NIDCR/CDC-grounded + clinic)
│   └── requirements.txt
├── frontend/
│   ├── app/                 # routes incl. /visit-confirmation
│   ├── src/
│   └── package.json
├── assets/brand/            # Ivory logo SVGs
├── design-system/ivory/     # design tokens + component specs
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

### Integrations (optional)

Copy `env.example` to `backend/.env` and fill in `AIRTABLE_API_KEY` /
`AIRTABLE_BASE_ID`, `CALCOM_API_KEY` / `CALCOM_EVENT_TYPE_ID`, and
`RESEND_API_KEY` to make `accept` create a real lead, booking request, and
confirmation email. Leave them unset for deterministic dry-run demo output.

## Validation

Backend integration coverage includes:

- health and reset endpoints
- all three intake flows end to end, through `accept` and the front-desk block
- interruption and resume behavior
- invalid input re-prompts (numbers, enums, emails, phone, free-text guards)
- service switching mid-flow
- `adjust` and `restart`
- protection against misclassification of flow-start and bare field replies
- compact multi-field input handling
- integration payload shapes (captured requests) and error degradation

Run the backend test suite from the repo root:

```bash
backend/.venv/bin/python -m pytest tests/ -q   # 56 passed
```

## Key Invariants

- backend state is the source of truth
- business results (visit estimates) are deterministic, not LLM-generated
- invalid field input must not advance the flow step
- mid-flow knowledge questions must not clear `collected_data`
- flow-start intents must not be downgraded into generic RAG
- integrations fire only on explicit `accept`, and never break the turn on failure
- the frontend renders backend state; it never invents flow state on its own

## Brand & Design

- [Brand guide](docs/branding/IVORY_BRAND.md) — name, voice, taglines, logo rules
- [Design system](design-system/ivory/MASTER.md) — tokens, components, checklists
- Logo assets in [`assets/brand/`](assets/brand/)

## Useful Docs

- [Dental vertical spec](docs/specs/DENTAL_VERTICAL_SPEC.md)
- [Engineering walkthrough](docs/ENGINEERING_WALKTHROUGH.md)
- [Intake flow test checklist](docs/guides/INTAKE_FLOW_TEST_CHECKLIST.md)
- [ASCII architecture](docs/architecture/ASCII_ARCHITECTURE.md)
- [Architecture decisions](docs/architecture/ARCHITECTURE_DECISIONS.md)
- [Plain-English overview](docs/layman/OVERVIEW_IN_PLAIN_ENGLISH.md)
- [Local run guide](docs/guides/LOCAL_RUN_INSTRUCTIONS.md)
- [Dental dataset research](docs/DATASET_RESEARCH_DENTAL.md)

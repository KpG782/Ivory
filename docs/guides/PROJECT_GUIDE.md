# Ivory Project Guide

## Purpose

This guide explains what the Ivory chatbot project is, how it works now, and which technology choices shape the current implementation.

It is meant to help a junior engineer quickly understand the project without reading every root-level markdown file first.

## Current Repository Status

The repository now contains the working application source code as well as the supporting design and audit docs.

Present now:
- `backend/` FastAPI + LangGraph backend
- `frontend/` Next.js frontend
- `tests/` backend integration tests
- `docs/` specs, guides, audits, and reports
- `docker-compose.backend.yml` and backend container files
- `env.example`

## Product Goal

The intended product is an AI front desk for Ivory Dental Studio.

It has two responsibilities:
- answer questions about dental care and the clinic
- guide patients through a visit-intake workflow

Example user behaviors:
- "What does a routine cleaning include?"
- "I'd like to book a cleaning."

The system is designed to handle both kinds of requests in one conversation.

## Core Architecture

The current architecture is a **LangGraph state machine** with two main modes:

- `conversational`
  Handles dental questions using RAG.

- `transactional`
  Handles the structured visit-intake flow.

### Why a state machine is used

Visit intake is not just open-ended chat. It is a step-by-step workflow with required fields, validation, and confirmation.

A state machine is useful because it:
- tracks the current step
- preserves structured data
- routes the user to the correct next action
- allows interruptions without losing progress

## Key Design Feature

The most important engineering behavior in this project is **graceful mid-flow switching**.

Example:
1. User starts a cleaning intake.
2. The bot collects patient details.
3. The user asks a dental question in the middle of the flow.
4. The bot answers the question.
5. The bot resumes the intake flow from the same step with previously collected data still intact.

This is the main feature that differentiates the design from a simple chatbot prompt wrapper.

## Intent Model

The system classifies each user message into one of three intents:

- `question`
  Dental or clinic question, routed to RAG.

- `intake`
  New or continued request to set up a visit.

- `response`
  Answer to a bot prompt during the intake flow.

The `response` intent is especially important. Without it, the system might mistake a field value like `"2024"` or `"Maria Santos"` for a new conversation request instead of intake data. In the implementation, this classification is fully deterministic — `nodes/router.py` maps (state, message) to a route with ordered rules and no LLM call.

## Graph Nodes

The current backend uses these nodes:

- `router`
  Makes the deterministic routing decision for the turn.

- `rag_answer`
  Retrieves relevant knowledge base content and generates a grounded answer (and re-asks the paused field when mid-intake).

- `identify_service`
  Determines the service type: cleaning, emergency, or cosmetic.

- `collect_details`
  Asks for the required fields for the selected service.

- `validate_visit`
  Validates the collected data and calculates the visit estimate.

- `confirm`
  Lets the user accept, adjust, or restart. Accept is the only place the front-desk integrations (Airtable, Cal.com, Resend) fire.

## State Shape

The conversation state includes fields such as:

- `messages`
- `mode`
- `intent`
- `intake_step`
- `service_type`
- `collected_data`
- `visit_estimate`
- `pending_question`

This state lets the application behave like a workflow engine rather than a stateless chatbot. It lives in the LangGraph checkpointer, keyed by `thread_id == session_id`.

## Retrieval and LLM Layer

The RAG design is:

- documents are stored in a knowledge base (12 dental docs, NIDCR/CDC grounded)
- embeddings are generated with `sentence-transformers`
- vectors are stored in `ChromaDB`
- retrieved context is passed to an LLM through `OpenRouter`

### Why this matters

This keeps dental answers grounded in source material instead of relying only on the model's general memory.

Benefits:
- better factual consistency
- easier content updates
- lower hallucination risk (important for medical-adjacent content — the assistant educates, it never diagnoses)

## Current Tech Stack

- Backend: Python, FastAPI, LangGraph
- LLM access: OpenRouter
- Embeddings: `sentence-transformers`
- Vector store: ChromaDB
- Frontend: Next.js, React, TypeScript, Tailwind CSS
- Streaming: SSE
- Integrations: Airtable, Cal.com, Resend (stdlib `urllib` clients with dry-run mode)
- Local orchestration: backend-focused Docker Compose

## Intake Flow Design

The intake flow is:

1. detect intake intent
2. identify the service
3. collect required fields
4. validate inputs
5. calculate the visit estimate
6. confirm, adjust, or restart
7. on accept: create the CRM lead, request the booking, send the confirmation email

### Intake inputs by service

Cleaning (routine exam & cleaning):
- patient name
- contact email
- last dental visit year
- insurance status (insured or self-pay)
- preferred time (morning, afternoon, evening)

Emergency (urgent visit):
- patient name
- contact phone
- issue type (toothache, chipped tooth, swelling, lost filling)
- pain level (0–10)
- insurance status

Cosmetic (consultation):
- patient name
- contact email
- treatment (whitening, veneers, aligners, bonding)
- budget band (basic, standard, premium)
- timeline (asap, this month, flexible)

## Visit Estimation

The estimator is a simple deterministic fee schedule:

`base_fee × factors`

For example, a cleaning starts at a base of 140, scaled by years since the last visit and by insurance status; an emergency visit starts at 110, scaled by issue type and pain level. Every estimate is a low–high range with the disclaimer that it is educational, not a diagnosis or final price.

This is a practical design choice because it keeps business logic deterministic while allowing the LLM to focus on answer prose.

## API and Frontend Design

The backend API includes:
- `POST /chat`
- `GET /health`
- `POST /reset`

The chat endpoint streams responses using **Server-Sent Events (SSE)** so the frontend can render tokens progressively.

The frontend is a React chat UI with components such as:
- chat window
- message bubble
- typing indicator
- visit card (with JSON/CSV export)

## Environment Variables

The repository includes `env.example` with these variables:

- `OPENROUTER_API_KEY` (required)
- `OPENROUTER_MODEL`
- `CHROMA_PERSIST_DIR`
- `REDIS_URL` (listed for session storage; the current backend keeps state in the in-memory LangGraph checkpointer)
- `ALLOWED_ORIGINS`, `RATE_LIMIT_ENABLED`, `RATE_LIMIT_CHAT`, `RATE_LIMIT_RESET`
- Front-desk integrations (all optional; unset = dry-run): `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`, `AIRTABLE_TABLE_NAME`, `CALCOM_API_KEY`, `CALCOM_EVENT_TYPE_ID`, `CLINIC_TIMEZONE`, `RESEND_API_KEY`, `RESEND_FROM`

### Important note

`env.example` is a sample configuration file, not a Python virtual environment.

Difference:
- `venv` = Python package environment
- `.env` or `env.example` = runtime configuration values

## Security Note

`env.example` is currently sanitized and uses placeholders only, which is the correct setup.

Recommended practice:
1. keep real secrets only in a local `.env` file
2. never commit live API keys into `env.example`
3. rotate any key immediately if it is ever exposed

## Strengths Of The Design

- clear separation between conversational and transactional behavior
- good use of explicit state management
- practical RAG architecture for domain-specific Q&A
- business logic kept outside the LLM
- integrations fire only on explicit accept, with safe dry-run and error degradation
- streaming response design improves perceived speed

## Current Gaps

The main remaining gaps are no longer core implementation gaps. They are mostly follow-up hardening items:

- durable shared session persistence for multi-instance deployment (persistent LangGraph checkpointer)
- broader browser/E2E automation
- deeper evaluation coverage for RAG answer quality
- async LLM HTTP client for high concurrency

## Recommended Next Steps

If you are extending the implementation, the most sensible order is:

1. read `docs/specs/DENTAL_VERTICAL_SPEC.md` (the binding spec)
2. study `ChatState` in `backend/state.py`
3. follow one turn through `graph.py` → `nodes/router.py` → a handler node
4. run the test suite (`backend/.venv/bin/python -m pytest tests/ -q` — 56 tests)
5. make changes with the tests as the safety net

## Short Explanation For A Junior Engineer

If you need to explain this quickly:

> This project is a full-stack AI dental front-desk assistant. It combines RAG-based dental Q&A with a structured visit-intake workflow powered by a LangGraph state machine. The main engineering goal is to preserve patient progress during intake even if the user interrupts the flow with dental questions, and to keep every business result — estimates and front-desk actions — deterministic.

## Short Explanation For A Non-Technical Person

> It is a chatbot for a dental clinic that can answer questions and help patients set up visits without losing progress if the conversation changes direction.

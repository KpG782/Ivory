# Architecture Decisions

## Why a state machine

This project is not just a chatbot. It has to support:

- open-ended insurance Q&A
- structured quote collection
- interruption and resume without losing state

That is why the backend uses explicit state and node-based orchestration instead of a prompt-only flow.

## Why deterministic routing comes first

The backend should not rely on the LLM for business-critical control flow.

That is why:

- product choice is detected deterministically
- quote collection steps are explicit
- confirm, adjust, and restart are explicit states

The LLM is mainly used in the conversational RAG path, not for quote math or workflow integrity.

## Why quote calculation is deterministic

Quote generation must be explainable and repeatable.

So the premium logic lives in [quote_calculator.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/services/quote_calculator.py), not in the LLM.

## Where state lives

The backend owns the session state using [state.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/state.py).

Important fields:

- `mode`
- `quote_step`
- `insurance_type`
- `current_field`
- `collected_data`
- `quote_result`
- `pending_question`

The frontend can cache snapshots for UX continuity, but it does not invent workflow state.

## Where validation happens

Validation has two layers:

- immediate field validation in [collect_details.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/collect_details.py)
- full quote validation in [validate_quote.py](/C:/Users/kpg78/Downloads/TENEXT/ivory-chatbot/backend/nodes/validate_quote.py)

This keeps the workflow strict without overcomplicating the codebase.

## Why this is minimal enough

The architecture stays intentionally small:

- one FastAPI backend
- one Next.js frontend
- one local vector store
- one in-memory session store

That is enough to demonstrate orchestration, guardrails, RAG, and transactional state correctness in a take-home submission.

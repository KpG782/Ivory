# Ivory Validation And Runbook

## Purpose

This runbook explains how to validate the Ivory implementation against the current specification and how to keep the local environment clean while the project is still being built.

It is written for a take-home style implementation workflow where the repo may still be incomplete in some areas.

## Environment Hygiene

### Python environment

- Use `backend/.venv` for all Python work.
- Create it with `python -m venv .venv` inside `backend/`.
- Activate it before installing or running any Python packages.
- Do not install Python packages globally.

### Configuration

- Use `.env` only for configuration values and secrets.
- Keep `.env` out of version control.
- `env.example` must remain placeholder-only.

### Git ignore expectations

The repository should ignore:
- `backend/.venv/`
- `.env`
- generated vector-store data
- Python cache files
- Node modules and build outputs

## Local Setup Checklist

1. Confirm Python 3.11+ and Node.js 18+ are installed.
2. Create and activate `backend/.venv`.
3. Install backend dependencies inside the active virtual environment.
4. Install frontend dependencies if the frontend exists.
5. Verify `env.example` contains placeholders only.
6. Confirm no secrets are committed to the repo.

## Validation Strategy

Because the repository currently contains spec and scaffolding material rather than a full application, validation is split into two layers:

- **Spec validation**
  Checks that the repository artifacts describe the expected architecture, contracts, and setup flow.

- **Implementation validation**
  Checks runtime behavior once backend/frontend code exists.

## Acceptance Areas

### Conversational RAG

Validate that:
- product questions use retrieval-backed answers
- retrieval failure degrades gracefully
- answers stay grounded in the knowledge base

### Quote flow

Validate that:
- auto, home, and life quote flows can start and finish
- required fields are collected step by step
- invalid fields are re-prompted
- quote calculation is deterministic

### Mid-flow switching

Validate that:
- a product question during quote collection does not reset the flow
- collected data survives the interruption
- the flow resumes at the previous step

### Session management

Validate that:
- multiple turns work in one session
- sequential quotes are possible
- `POST /reset` clears only one session

### Streaming and UX

Validate that:
- `POST /chat` streams over SSE
- `token`, `message_complete`, and `error` events are stable
- the UI can render both streaming content and final quote payloads

## Manual Validation Scenarios

1. Ask what insurance products are offered.
2. Start an auto quote and answer each field.
3. Start a home quote and answer each field.
4. Start a life quote and answer each field.
5. Ask a product question while a quote is in progress.
6. Submit an invalid field value and verify targeted re-prompting.
7. Accept a quote and start another one in the same session.
8. Reset a session and verify prior state is cleared.
9. Force retrieval failure and verify graceful fallback behavior.
10. Force OpenRouter failure and verify controlled error handling.

## Automated Validation Targets

When implementation exists, automated checks should cover:
- endpoint contract tests
- state transition tests
- retrieval fallback tests
- quote calculator tests
- SSE event contract tests
- reset/session isolation tests

## Expected Runtime Contracts

### `POST /chat`

- request body includes `message` and `session_id`
- response is `text/event-stream`
- event names are `token`, `message_complete`, and `error`

### `POST /reset`

- request body includes `session_id`
- only the targeted session is cleared

### `GET /health`

- returns readiness status for the app

### `ChatState`

The implementation should preserve the canonical state shape defined in `docs/specs/IMPLEMENTATION_SPEC.md`.

## Failure Handling Expectations

- invalid input should not break the entire conversation
- missing retrieval data should not crash the assistant
- LLM errors should produce a user-safe recovery message
- state corruption should reset the affected session only

## Verification Notes For Reviewers

- If backend/frontend code is missing, validate the spec and scaffolding instead of treating runtime checks as failed.
- If a future implementation diverges from this runbook, update the spec first, then update the runbook and tests together.

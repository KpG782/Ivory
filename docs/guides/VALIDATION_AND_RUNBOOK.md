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
- The front-desk integration keys (`AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`, `AIRTABLE_TABLE_NAME`, `CALCOM_API_KEY`, `CALCOM_EVENT_TYPE_ID`, `RESEND_API_KEY`, `RESEND_FROM`) are optional — leave them unset for dry-run demo mode.

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
- dental questions use retrieval-backed answers
- retrieval failure degrades gracefully
- answers stay grounded in the knowledge base

### Intake flow

Validate that:
- cleaning, emergency, and cosmetic intake flows can start and finish
- required fields are collected step by step
- invalid fields are re-prompted
- visit estimation is deterministic

### Mid-flow switching

Validate that:
- a dental question during intake collection does not reset the flow
- collected data survives the interruption
- the flow resumes at the previous step

### Front-desk integrations

Validate that:
- Airtable, Cal.com, and Resend fire only on an explicit `accept`
- missing keys produce `dry_run` results with no network calls
- an integration error still lets the accept turn succeed

### Session management

Validate that:
- multiple turns work in one session
- sequential intakes are possible
- `POST /reset` clears only one session

### Streaming and UX

Validate that:
- `POST /chat` streams over SSE
- `token`, `message_complete`, and `error` events are stable
- the UI can render both streaming content and final visit-estimate payloads

## Manual Validation Scenarios

1. Ask what dental services are offered.
2. Start a cleaning intake and answer each field.
3. Start an emergency intake and answer each field.
4. Start a cosmetic intake and answer each field.
5. Ask a dental question while an intake is in progress.
6. Submit an invalid field value and verify targeted re-prompting.
7. Accept an estimate, verify the "Front desk actions" block, and start another intake in the same session.
8. Reset a session and verify prior state is cleared.
9. Force retrieval failure and verify graceful fallback behavior.
10. Force OpenRouter failure and verify controlled error handling.

## Automated Validation Targets

When implementation exists, automated checks should cover:
- endpoint contract tests
- state transition tests
- retrieval fallback tests
- visit estimator tests
- front-desk integration tests (dry-run, payload, and error paths)
- SSE event contract tests
- reset/session isolation tests

The current suite (`backend/.venv/bin/python -m pytest tests/ -q`) covers these areas with 52 passing tests.

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

The implementation should preserve the canonical state shape defined in `docs/specs/DENTAL_VERTICAL_SPEC.md` (`intake_step`, `service_type`, `collected_data`, `visit_estimate`, ...).

## Failure Handling Expectations

- invalid input should not break the entire conversation
- missing retrieval data should not crash the assistant
- LLM errors should produce a user-safe recovery message
- integration errors should degrade to an `error` line in the front-desk block, never a failed turn
- state corruption should reset the affected session only

## Verification Notes For Reviewers

- If backend/frontend code is missing, validate the spec and scaffolding instead of treating runtime checks as failed.
- If a future implementation diverges from this runbook, update the spec first, then update the runbook and tests together.

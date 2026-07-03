# Test Coverage

This folder contains the contract scaffold and executable backend integration tests for the Ivory Dental Front Desk assistant.

The frontend browser flow is still primarily a manual test path, but the Python suite covers the implemented FastAPI backend contracts directly.

## Contents

- `validation_scenarios.md`
  Human-readable scenario matrix covering RAG, the intake flow, mid-flow switching, reset behavior, front-desk integrations, and failure handling.

- `test_contract_scaffold.py`
  Lightweight contract scaffold that keeps the intended public surface explicit (state keys, intents, intake steps, service types, endpoints, SSE events) and cross-checks it against the implemented backend.

- `test_backend_integration.py`
  Executable FastAPI integration tests for health, reset, SSE chat, the three intake flows (cleaning, emergency, cosmetic), visit estimates, mid-flow interruption handling, the invalid-input matrix, and the accept-time front-desk integrations (Airtable, Cal.com, Resend).

## What the backend suite exercises

- `POST /chat` (SSE), `POST /reset`, `GET /health`
- SSE event streams (`token` first, `message_complete` last)
- State transitions and deterministic visit estimates
- Interruption + exact resume of the pending intake field
- Validation re-prompts that never advance the flow step
- `accept` / `adjust` / `restart` after an estimate exists
- Front-desk integrations on `accept`: dry-run lines when unconfigured, real
  payload shapes when configured (with `urllib.request.urlopen` mocked), and
  graceful `error` reporting when one integration fails

The tests stub retrieval and the LLM client (`nodes.rag._build_client_or_none`, `nodes.rag.search_knowledge_base`) and mock all outbound HTTP so they remain deterministic and run fully offline.

## Running

```bash
cd /path/to/Ivory
backend/.venv/bin/python -m pytest tests/ -q
```

## Environment Assumptions

- Python tests run inside `backend/.venv`.
- Configuration comes from `.env`, not from committed secrets.
- Integration env keys (`AIRTABLE_*`, `CALCOM_*`, `RESEND_*`) are scrubbed by the test fixture, so a locally configured `.env` never causes live network calls during tests.

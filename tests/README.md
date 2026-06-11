# Test Coverage

This folder contains both spec scaffolding and executable backend integration tests for the Ivory Insurance Assistant.

The frontend browser flow is still primarily a manual test path, but the Python suite now covers the implemented FastAPI backend contracts directly.

## Contents

- `validation_scenarios.md`
  Human-readable scenario matrix covering RAG, quote flow, mid-flow switching, reset behavior, and failure handling.

- `test_contract_scaffold.py`
  Lightweight contract scaffold that keeps the intended public surface explicit.

- `test_backend_integration.py`
  Executable FastAPI integration tests for health, reset, SSE chat, quote generation, and mid-flow interruption handling.

## Intended Future Use

The backend test suite now exercises these implemented contracts directly:
- call `POST /chat`
- call `POST /reset`
- verify SSE event streams
- verify state transitions and quote results

The tests stub external retrieval and LLM calls so they remain deterministic and do not require live network access.

## Environment Assumptions

- Python tests should run inside `backend/.venv` once the backend exists.
- Configuration should come from `.env`, not from committed secrets.

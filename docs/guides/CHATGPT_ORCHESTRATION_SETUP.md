# ChatGPT Orchestration Setup

## Purpose

This guide shows how to set up your main ChatGPT orchestrator and subagents for implementing the Ivory project using the repository spec as the source of truth.

Use [`docs/specs/DENTAL_VERTICAL_SPEC.md`](../specs/DENTAL_VERTICAL_SPEC.md) as the authoritative build contract. (The older [`docs/specs/IMPLEMENTATION_SPEC.md`](../specs/IMPLEMENTATION_SPEC.md) predates the dental conversion and is kept for history.)

## Files In This Setup

- `docs/prompts/main_orchestrator.md`
- `docs/prompts/subagent_backend_core.md`
- `docs/prompts/subagent_rag_services.md`
- `docs/prompts/subagent_frontend.md`
- `docs/prompts/subagent_quality_infra.md`

## What To Configure In ChatGPT

### Main orchestrator

Create one main orchestrator agent and use the contents of:

- `docs/prompts/main_orchestrator.md`

Its role is to:
- read the implementation spec first
- break work into execution phases
- assign tasks to subagents
- enforce shared contracts
- integrate completed work

### Subagents

Create four subagents using these prompts:

- Backend Core: `docs/prompts/subagent_backend_core.md`
- RAG Services: `docs/prompts/subagent_rag_services.md`
- Frontend: `docs/prompts/subagent_frontend.md`
- Quality/Infra: `docs/prompts/subagent_quality_infra.md`

## Recommended Flow

### Stage 1: Load spec

The main orchestrator must read:
- `docs/specs/DENTAL_VERTICAL_SPEC.md`

It should treat that file as the implementation source of truth.

### Stage 2: Lock contracts

Before parallel work begins, the orchestrator should confirm:
- `ChatState` shape
- endpoint shapes
- SSE event names
- virtual environment path `backend/.venv`
- session model keyed by `session_id`

### Stage 3: Start backend core

Run Backend Core first to establish:
- backend structure
- API skeleton
- LangGraph structure
- intake workflow

### Stage 4: Parallelize safely

Once contracts are stable:
- RAG Services can implement ingestion/retrieval
- Frontend can implement the SSE chat UI
- Quality/Infra can implement tests, logs, and environment hygiene

### Stage 5: Integrate

The orchestrator should merge results only after checking:
- shared contracts were followed
- no subagent changed architecture without approval
- tests and validations match the spec

## Standard Reporting Format

Require every subagent to return status in this structure:

```text
Workstream:
Files changed:
Contracts used:
Tests run:
Blocked by:
Notes:
```

## Non-Negotiable Rules

The orchestrator should enforce these rules:

- `docs/specs/DENTAL_VERTICAL_SPEC.md` is the source of truth
- Python virtual environment must be `backend/.venv`
- `.env` is config only, not the Python runtime
- visit estimation stays deterministic outside the LLM
- `POST /chat`, `POST /reset`, and `GET /health` must match the spec
- SSE event names must remain stable
- `ChatState` shape must stay consistent unless the orchestrator explicitly approves a change

## Suggested First Message To The Main Orchestrator

```text
Read docs/specs/DENTAL_VERTICAL_SPEC.md first and treat it as the implementation source of truth.

Use the subagent roles already defined in the repo prompt files:
- Backend Core
- RAG Services
- Frontend
- Quality/Infra

Your job is to:
1. break the project into execution phases,
2. assign the first tasks,
3. enforce shared contracts,
4. integrate results,
5. verify acceptance criteria from the spec.

Do not redesign the architecture unless a real implementation conflict appears.
```

## Recommended Execution Sequence

1. Backend Core
2. Backend Core + Quality/Infra contract check
3. RAG Services and Frontend in parallel
4. Quality/Infra integration checks
5. Final orchestrator acceptance pass against `docs/specs/DENTAL_VERTICAL_SPEC.md`

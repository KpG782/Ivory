# Prompt Pack Overview

This folder contains the prompt pack for setting up a main ChatGPT orchestrator and four implementation subagents for the Ivory project.

## Source Of Truth

All prompts in this folder assume that:

- `docs/specs/IMPLEMENTATION_SPEC.md` is the implementation source of truth

## Prompt Files

- `main_orchestrator.md`
  Main coordinator prompt. Reads the spec, locks contracts, assigns work, and integrates results.

- `subagent_backend_core.md`
  Backend structure, API contracts, LangGraph flow, session handling, and deterministic quote logic.

- `subagent_rag_services.md`
  Knowledge base ingestion, embeddings, ChromaDB, retrieval, and grounded answer behavior.

- `subagent_frontend.md`
  React UI, SSE event handling, message rendering, and reset/quote UX.

- `subagent_quality_infra.md`
  Validation scenarios, setup hygiene, trace/log expectations, and rate-limit/test scaffolding.

## Recommended Order

1. Start with `main_orchestrator.md`
2. Have the orchestrator read `docs/specs/IMPLEMENTATION_SPEC.md`
3. Start `subagent_backend_core.md`
4. Lock contracts
5. Run `subagent_rag_services.md` and `subagent_frontend.md` when dependencies are ready
6. Run `subagent_quality_infra.md` for validation and acceptance checks

## Key Rules

- Python setup must use `backend/.venv`
- `.env` is config only
- endpoint and SSE contracts must remain stable
- quote calculation must stay outside the LLM
- subagents must report blockers instead of silently changing contracts

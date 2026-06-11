# Ivory ASCII Architecture

This document reflects the current implementation in this repository.

## Top-Level System

```text
┌──────────────────────────────────────────────────────────────────────┐
│                           User Browser                              │
│                    Next.js UI on http://localhost:3000              │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                │ POST /api/chat, /api/reset
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Frontend Proxy Layer                           │
│              frontend/app/api/chat + frontend/app/api/reset         │
│      Keeps frontend contract stable while forwarding to FastAPI     │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                │ POST /chat, /reset
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                             │
│                         backend/main.py                             │
│                                                                      │
│  /health  -> health check                                            │
│  /reset   -> resets one session                                      │
│  /chat    -> runs orchestration and streams SSE                      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                │ run_graph(state, message)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Orchestration / State Machine                    │
│                         backend/graph.py                            │
│                                                                      │
│  Single source of truth: ChatState                                   │
│  mode | quote_step | insurance_type | current_field | collected_data │
│  quote_result | pending_question | messages | trace_id               │
└───────────────┬───────────────────────────────┬──────────────────────┘
                │                               │
                │ conversational                │ transactional
                ▼                               ▼
┌──────────────────────────────┐     ┌────────────────────────────────┐
│ RAG Path                     │     │ Quote Workflow Path             │
│ backend/nodes/rag.py         │     │ backend/nodes/*                │
│                              │     │                                │
│ 1. retrieve KB chunks        │     │ 1. identify product            │
│ 2. rerank results            │     │ 2. collect current field       │
│ 3. LLM grounded answer       │     │ 3. validate before commit      │
│ 4. fallback answer if needed │     │ 4. deterministic quote calc    │
└───────────────┬──────────────┘     │ 5. confirm / adjust / restart  │
                │                    └────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     Retrieval / Knowledge Base                       │
│                backend/services/vectorstore.py                       │
│                                                                      │
│  knowledge_base/*.md -> chunks -> embeddings -> Chroma collection    │
│  search_knowledge_base(query) -> relevant chunks for RAG answer       │
└──────────────────────────────────────────────────────────────────────┘
```

## Runtime Flow

```text
User sends message
    │
    ▼
FastAPI /chat
    │
    ▼
load session from SESSION_STORE
    │
    ▼
run_graph(state, message)
    │
    ├─ classify_intent(...)
    ├─ question -> rag_answer(...)
    ├─ quote start -> identify_product(...)
    ├─ collect -> collect_details(...)
    ├─ validate -> validate_quote(...)
    └─ confirm -> confirm(...)
    │
    ▼
save updated state
    │
    ▼
stream assistant message via SSE
    │
    ▼
frontend updates chat, quote summary, and session snapshot
```

## Transactional Invariant

```text
read current_field
    │
    ▼
validate current input
    │
    ├─ invalid -> re-prompt same field
    └─ valid -> store in collected_data
                 │
                 ▼
             compute next missing field
                 │
                 ├─ found -> ask next field
                 └─ none  -> validate full quote and generate result
```

This prevents the late-validation bug where the app asks the next question before the previous field is truly valid.

## Mid-Flow Interruption

```text
quote in progress
    │
    ├─ user asks policy question
    ▼
RAG answers question
    │
    ▼
graph appends exact resume prompt for the pending field
    │
    ▼
user continues same quote without losing collected_data
```

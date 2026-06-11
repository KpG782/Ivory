# CLAUDE.md — Project Context for Claude Code

## What This Project Is

Ivory Insurance Assistant — a LangGraph-based chatbot for a take-home assessment (Mid-Level Software Engineer role). The bot has two modes:

1. **Conversational (RAG)** — answers questions about insurance products using vector search over a knowledge base
2. **Transactional (Quote Flow)** — structured workflow to collect customer info and generate insurance quotes

The orchestrator is a **LangGraph state machine** that routes between these modes based on detected user intent.

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, LangGraph, ChromaDB, sentence-transformers
- **LLM:** OpenRouter API (model specified via env var)
- **Frontend:** Next.js App Router + React + TypeScript + Tailwind CSS
- **Streaming:** Server-Sent Events (SSE) from FastAPI to frontend

## Key Architecture Concepts

### State Schema (`backend/state.py`)
```python
class ChatState(TypedDict):
    messages: list              # conversation history
    mode: str                   # "conversational" | "transactional"
    intent: str                 # "question" | "quote" | "response"
    quote_step: str             # "identify" | "collect" | "validate" | "confirm"
    insurance_type: str | None  # "auto" | "home" | "life"
    collected_data: dict        # accumulated form fields
    quote_result: dict | None   # generated quote
    pending_question: str|None  # RAG question asked mid-flow
```

### Graph Nodes
- `router` — classifies intent, routes to correct node
- `rag_answer` — retrieves from ChromaDB, generates answer via LLM
- `identify_product` — determines which insurance type
- `collect_details` — collects product-specific fields step by step
- `validate_quote` — validates inputs, computes premium
- `confirm` — presents quote, handles accept/adjust/restart

### Critical Behavior: Mid-Flow Transitions
When a user asks a RAG question while in the quote flow:
1. State preserves `collected_data`, `quote_step`, and `insurance_type`
2. Routes to `rag_answer` to answer the question
3. Returns to the exact quote step with all data intact
This is the key differentiator the assessment evaluates.

## File Structure

```
backend/
  main.py              — FastAPI app, SSE endpoint at POST /chat
  graph.py             — LangGraph graph definition with all edges
  state.py             — ChatState TypedDict
  nodes/               — One file per graph node
  services/
    llm.py             — OpenRouter client wrapper
    vectorstore.py     — ChromaDB init, ingestion, retrieval
    quote_calculator.py — Premium calculation (base rates × risk factors)
  knowledge_base/      — markdown knowledge-base files about Ivory Insurance

frontend/
  app/
    page.tsx           — Main page entry
    api/               — Proxy routes to backend
  src/
    App.tsx            — Main app shell
    components/        — ChatWindow, MessageBubble, TypingIndicator, QuoteCard
    hooks/useChat.ts   — SSE streaming hook
```

## Environment Variables

```
OPENROUTER_API_KEY=     # Required. Provided by assessment.
OPENROUTER_MODEL=       # Optional. Default: meta-llama/llama-3.1-8b-instruct (or similar)
CHROMA_PERSIST_DIR=     # Optional. Default: ./vectorstore
```

## Commands

```bash
# Backend
cd backend && pip install -r requirements.txt
python -c "from services.vectorstore import ingest_knowledge_base; ingest_knowledge_base()"
uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Backend container only
docker compose -f docker-compose.backend.yml up --build
```

## API Endpoints

- `POST /chat` — SSE streaming endpoint. Body: `{ "message": string, "session_id": string }`
- `GET /health` — Health check
- `POST /reset` — Reset session state

## Coding Conventions

- Python: type hints everywhere, snake_case, docstrings on public functions
- TypeScript: strict mode, functional components, named exports
- State mutations only happen in node functions, never in edge conditions
- All LLM calls go through `services/llm.py` — never call OpenRouter directly from nodes
- Validation logic lives in `services/quote_calculator.py`, not in nodes

## Common Pitfalls

- **Don't use LangChain's AgentExecutor.** This project uses LangGraph's `StateGraph` directly.
- **Don't reset `collected_data` when switching to RAG mode.** That's the whole point of graceful transitions.
- **Intent classifier must include "response" intent** — otherwise "2019 Toyota Camry" gets misrouted as a new intent instead of a form response.
- **ChromaDB collection must be created before first query.** Run the ingestion script first.
- **SSE responses must flush after each token.** Use `StreamingResponse` with proper `media_type="text/event-stream"`.

## Testing

Manual testing scenarios are in README.md. Key paths to verify:
1. Pure RAG conversation
2. Full quote flow (auto, home, life)
3. Mid-flow RAG question → resume quote
4. Invalid input handling
5. Quote restart / sequential quotes

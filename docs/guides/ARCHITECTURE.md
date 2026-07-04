# Ivory Dental Front Desk — Architecture & Engineering Review

## 1. Executive Summary

Ivory is a hybrid dental front-desk chatbot that answers grounded knowledge-base questions (RAG) and runs a structured, multi-step visit-intake workflow (transactional), switching between the two modes in the same session without losing state. Built as a take-home technical assessment demonstrating LLM orchestration, deterministic business logic, streaming API design, external integrations with safe dry-run degradation, and production-grade hardening.

**Core tech stack:** Python FastAPI + LangGraph · OpenRouter · ChromaDB + sentence-transformers · Airtable / Cal.com / Resend · Next.js App Router + React + Tailwind CSS

**Key architectural pattern:** Backend-controlled state machine (LangGraph `StateGraph`) with a Next.js BFF proxy sitting in front of it and a React streaming UI that renders what the backend tells it. The LLM writes prose only; deterministic Python owns control flow, validation, estimates, and integrations.

---

## 2. System Architecture

### High-Level Data Flow

```
Browser (React)
    │
    │  POST /api/chat  (SSE)
    ▼
Next.js App Router (BFF Proxy)
app/api/chat/route.ts          ← validates session cookie, forwards request
    │
    │  POST http://BACKEND_API_BASE_URL/chat
    ▼
FastAPI (Python)
main.py  /chat endpoint
    │  slowapi rate limiter (60/min per IP)
    │
    │  run_graph in thread-pool executor
    │  on_token callback → asyncio.Queue → SSE tokens
    ▼
LangGraph StateGraph (graph.py)
    │
    ├─► router node            deterministic route decision (no LLM)
    │       │
    │       ├─► rag_answer         [question / answer_then_resume]
    │       │       ├─ ChromaDB search
    │       │       ├─ OpenRouter streaming (real tokens via on_token callback)
    │       │       └─ mid-intake: re-appends the paused field prompt
    │       │
    │       ├─► identify_service   [start_intake / identify]
    │       │
    │       ├─► collect_details    [collect]
    │       │       └─ field validation + coercion
    │       │
    │       ├─► validate_visit     [step=validate]
    │       │       └─ visit_estimator (deterministic fee schedule)
    │       │
    │       └─► confirm            [step=confirm]
    │               └─ on accept: front_desk → Airtable / Cal.com / Resend
    │                              (dry-run without keys, error-tolerant)
    ▼
Updated ChatState → persisted by the LangGraph checkpointer (thread_id == session_id)
    │
    ▼
SSE stream to browser:
  event: token          (real LLM deltas for RAG / simulated for deterministic responses)
  event: message_complete   (full payload + visit_estimate + session snapshot)
```

### Component Breakdown

| Component | File(s) | Responsibility |
|-----------|---------|----------------|
| FastAPI app | `backend/main.py` | HTTP endpoints, rate limiting, real SSE streaming, `SESSION_STORE` view |
| LangGraph orchestrator | `backend/graph.py` | Compiles and runs the state machine; checkpointer is the session store |
| State schema | `backend/state.py` | `ChatState` TypedDict, `build_initial_state`, `clone_state` |
| Streaming context | `backend/streaming_context.py` | Thread-local on_token callback (bridges asyncio ↔ thread pool) |
| Deterministic router | `backend/nodes/router.py` | Ordered rules mapping (state, message) → route; pure function, no LLM |
| RAG node | `backend/nodes/rag.py` | Retrieves KB chunks, streams LLM answer via on_token, fallback to formatted text |
| Service identifier | `backend/nodes/identify_service.py` | Keyword-based service detection: cleaning, emergency, cosmetic |
| Field collector | `backend/nodes/collect_details.py` | Step-by-step data gathering with per-type/per-field validation and compact multi-field parsing |
| Visit validator | `backend/nodes/validate_visit.py` | Cross-field validation before estimation |
| Confirmation handler | `backend/nodes/confirm.py` | accept / adjust / restart logic; renders the "Front desk actions" block |
| LLM client | `backend/services/llm.py` | `OpenRouterClient` — stdlib HTTP, retry, streaming via `_stream_chat_text` |
| Vector store | `backend/services/vectorstore.py` | ChromaDB with sentence-transformers + hash-embedding fallback |
| Visit estimator | `backend/services/visit_estimator.py` | Deterministic fee-schedule estimates for cleaning/emergency/cosmetic |
| Front-desk orchestrator | `backend/services/front_desk.py` | Runs the three integrations on accept; never raises |
| Integration clients | `backend/services/airtable.py` `calcom.py` `resend_email.py` | Thin stdlib clients; dry-run without keys, `error` results on failure |
| Knowledge base | `backend/knowledge_base/*.md` | 12 Markdown documents (clinic overview, services, pricing, health education) |
| Session store view | `backend/main.py` `_CheckpointSessionView` | Dict-like view reading/writing straight through the checkpointer |
| Next.js BFF proxy | `frontend/app/api/chat/route.ts` `frontend/app/api/reset/route.ts` | Thin proxy — hides backend URL, avoids CORS, requires the session cookie |
| Auth routes | `frontend/app/api/auth/login/route.ts` `check/route.ts` `logout/route.ts` | Server-side credential validation, httpOnly cookie management |
| Auth helper | `frontend/app/api/auth/_auth.ts` | HMAC-SHA256 session token, constant-time comparison |
| Chat hook | `frontend/src/hooks/useChat.ts` | All client state: messages, session, SSE streaming, localStorage persistence |
| App shell | `frontend/src/App.tsx` | Login screen (cookie-based auth), sidebar, chat layout, flow/status chips |
| Auth lib | `frontend/src/lib/demoAuth.ts` | Client-side helpers: `checkAuthStatus`, `serverLogin`, `serverLogout` |
| Types | `frontend/src/types.ts` | `ChatMessage`, `SessionSnapshot`, `VisitEstimate`, `SavedChatSession` |

### How Components Communicate

- **Frontend → Backend:** HTTP POST via Next.js server-side proxy (no direct browser-to-FastAPI calls)
- **Backend nodes:** Direct Python function calls within the LangGraph execution
- **LLM streaming:** `on_token` callback stored in thread-local (`streaming_context.py`); RAG node pushes deltas; asyncio queue bridges to SSE generator
- **State passing:** Immutable clone on each node (`clone_state` + `deepcopy`)
- **Sessions:** The LangGraph checkpointer (`MemorySaver`), keyed by `thread_id == session_id`, is the single source of truth; `run_graph` loads the checkpoint, invokes the graph, and the result is persisted atomically
- **Integrations:** `confirm` → `front_desk.process_accept` → three clients; results come back as `IntegrationResult(name, status, detail)` and are rendered verbatim in chat

---

## 3. Technical Decisions & Trade-offs

### Decision: LangGraph StateGraph for orchestration

- **What:** Compiled `StateGraph` with 6 named nodes and conditional edges, plus a checkpointer for durable per-session memory.
- **Why:** The intake workflow is a genuine state machine — current step, field, and mode determine what happens next. LangGraph makes transitions explicit and testable rather than buried in if/else chains, and the checkpointer removes the need for a hand-rolled session store.
- **Trade-off:** Adds a framework dependency. Simple operations trigger a full graph invocation.
- **Alternative considered:** Plain Python functions with manual routing — simpler to start, harder to reason about as states multiply.
- **When to revisit:** If the workflow gains more than ~10 states or needs parallel branches.

---

### Decision: OpenRouter instead of direct OpenAI or Anthropic API

- **What:** All LLM calls go through `https://openrouter.ai/api/v1/chat/completions`. The code default model is `openai/gpt-4o-mini`; the Docker deployment defaults to `meta-llama/llama-3.1-8b-instruct` via `OPENROUTER_MODEL`.
- **Why:** Single API key across many models. For an assessment, lets the reviewer use their own key without provider lock-in. Small models keep costs very low.
- **Trade-off:** Routing middleman adds slight latency. Small models have lower instruction-following reliability than frontier models.
- **Alternative considered:** Direct OpenAI API — provider-locked.
- **When to revisit:** If answer quality on edge cases becomes a problem — it's an env-var swap.

---

### Decision: Fully deterministic routing (no LLM on the control path)

- **What:** `nodes/router.py` `decide()` maps (state, message) to exactly one route per turn using ordered rules: restart wins; a `?` while a field is pending is always answered-then-resumed (even if it mentions booking words); whole-word booking hints start or switch an intake; a pending field absorbs the reply; confirm-step negations never read as accept.
- **Why:** LLMs frequently misclassify short inputs like "2024" or "morning" as questions. A pure function is testable, reproducible, and free — the same inputs always produce the same route.
- **Trade-off:** Keyword rules must be curated (word-boundary matching so "Booker" doesn't trigger "book"). Exotic phrasings without a hint word fall to RAG.
- **Alternative considered:** LLM classification with deterministic overrides — rejected; the override list grew until the LLM had nothing left to decide.

---

### Decision: Deterministic visit estimator (not LLM-generated)

- **What:** `services/visit_estimator.py` uses a fixed fee schedule: base fee × factors (years since last visit, insurance status, issue type, pain level, treatment, budget band, timeline). The LLM never touches estimate numbers.
- **Why:** A patient-facing cost range must be reproducible, auditable, and explainable. LLM-generated numbers are hallucinations with no basis. Every estimate carries "Educational estimate — not a diagnosis or a final price."
- **Trade-off:** Simplified fees (no real fee schedule, no insurance plan tables). But for a demo this is correct — the output is predictable and defensible.
- **When to revisit:** In a real product, integrate the clinic's actual fee schedule and insurance adjudication.

---

### Decision: Real LLM streaming via thread-local on_token callback

- **What:** `OpenRouterClient._stream_chat_text()` uses OpenRouter's streaming API (`"stream": True`). Tokens are pushed to an `asyncio.Queue` via `loop.call_soon_threadsafe`. The SSE generator drains the queue in real time. For deterministic responses (field prompts, validation errors, estimates), word-by-word simulation is kept for UX consistency.
- **Why:** Eliminates the 1-3 second blank gap before the first token appears. The `streaming_context.py` thread-local stores the callback so it reaches deep into the LangGraph execution without modifying `ChatState` or the graph signatures.
- **Trade-off:** Slightly more complex request handling. LangGraph `invoke()` still runs synchronously in a thread-pool worker — the asyncio and threading layers must coordinate correctly.
- **Alternative considered:** Keep simulated streaming. Rejected because it degrades perceived responsiveness significantly.

---

### Decision: LangGraph checkpointer as the only session store

- **What:** `SESSION_STORE` in `main.py` is a `_CheckpointSessionView` — a dict-like view that reads and writes straight through the graph's checkpointer. There is no separate session dict to keep in sync.
- **Why:** Two stores for one piece of state is a consistency bug waiting to happen. The checkpointer already persists state atomically per turn; making it the single source of truth removed the manual save step entirely.
- **Trade-off:** The default checkpointer is `MemorySaver` — in-process, lost on restart. Horizontal scaling requires swapping in a persistent checkpointer (Redis/Postgres), which LangGraph supports without changing the graph code.
- **When to revisit:** Before any multi-instance deployment.

---

### Decision: Accept-only integrations with dry-run degradation

- **What:** `front_desk.process_accept` runs exactly three integrations — Airtable CRM lead, Cal.com booking request, Resend confirmation email — and only from the confirm node's accept branch. Missing env keys → `dry_run` (no network call); request failures → `error` result; the emergency flow (phone-only contact) → email `skipped`. The accept turn always succeeds.
- **Why:** External side effects need an explicit user action, and a demo must never hard-require third-party keys. The deterministic "Front desk actions" block makes the outcome visible either way.
- **Trade-off:** The Cal.com start time is computed deterministically (next business day at 09:00/13:00/17:00 UTC) rather than queried from real availability.
- **When to revisit:** Real availability lookup and idempotency keys for retries in production.

---

### Decision: Server-side auth with httpOnly cookie

- **What:** Credentials (`AUTH_USERNAME` / `AUTH_PASSWORD`) live in server-side env vars. The Next.js `/api/auth/login` route validates them and sets an `httpOnly; SameSite=Lax` session cookie. The session token is an HMAC-SHA256 of the credentials — stateless, no token store required. The `/api/chat` and `/api/reset` proxies require the same cookie because intake carries PII.
- **Why:** The previous design stored `NEXT_PUBLIC_IVORY_LOGIN_PASS` — meaning the password was bundled into client-side JavaScript. That's a critical security gap. Moving validation server-side and using `httpOnly` cookies means the password never reaches the browser.
- **Trade-off:** Requires the Next.js server to handle auth, not just act as a static host.
- **Alternative considered:** JWT with a database of sessions. Correct for multi-user production; stateless HMAC token is sufficient for single-user demo auth.

---

### Decision: `slowapi` rate limiting (60/min chat, 20/min reset)

- **What:** FastAPI endpoints are decorated with `@limiter.limit(...)`. The key function is `get_remote_address`. Rate limiting can be disabled via `RATE_LIMIT_ENABLED=false` for tests (read at request time).
- **Why:** Without rate limiting, a script can exhaust an OpenRouter API key in minutes. 60/min is 1 message per second on average — far above what a real user needs, while blocking automated abuse.
- **Trade-off:** Adds a dependency. Per-IP rate limiting is imprecise behind shared NAT. For production, per-session-ID limiting would be more accurate.

---

### Decision: Next.js BFF proxy (no direct browser-to-FastAPI calls)

- **What:** The frontend never calls FastAPI directly. All requests go through `/api/chat` and `/api/reset`, which also enforce the session cookie.
- **Why:** Keeps the backend URL off the client. Enables deploying frontend and backend to different hosts without touching React code. Avoids CORS issues. Adds an auth gate in front of PII-carrying requests.
- **Trade-off:** Adds a network hop. The proxy routes are thin (~40 lines each).

---

## 4. Strengths (What's Done Well)

**Graceful mode switching without state loss**
`graph.py` `_rag_node` — When a question arrives mid-intake, the RAG node answers it then re-appends the current field prompt ("Now, back to your cleaning visit intake — ..."). The intake pointer (`current_field`, `collected_data`) is untouched throughout. `test_mid_flow_question_preserves_intake_progress` validates this end-to-end, and `test_midflow_question_with_booking_word_answers_then_resumes` proves even booking-word questions can't hijack the flow.

**Deterministic routing with word-boundary guards**
`nodes/router.py` `decide()` — pure function, seven ordered rules, no LLM. "Booker Smith" is a name, "no, this is not ok" is never an accept, and `test_routing_is_a_pure_function_without_any_llm` asserts the routing table literally.

**Input validation at two independent layers**
First: `collect_details.py` — type coercion + range + allowed-value validation at entry, re-prompting without advancing; question-shaped and domain-word answers rejected for text fields ("i like dogs" is not a patient name). Second: `validate_visit.py` → `validate_visit_inputs` — cross-field pass before estimation.

**Exhaustive integration test suite**
`tests/` — 56 tests (45 integration + 7 contract scaffold), all offline. Cover all three intake flows, mid-flow interruption with exact resume text, the invalid-input matrix, service switching, adjust/restart/accept, compact multi-field input for every service, RAG fallback, and the front-desk integrations (dry-run, real payloads via monkeypatched urllib, and error paths).

**Real LLM streaming**
`services/llm.py` `_stream_chat_text` + `streaming_context.py` — Tokens arrive from OpenRouter as they are generated and are immediately forwarded to the browser. No blank gap before the first word appears.

**Resilient RAG pipeline with multiple fallbacks**
`services/vectorstore.py` and `nodes/rag.py` — sentence-transformers → hash-embedding fallback; ChromaDB dimension mismatch auto-recovery; LLM failure → formatted chunk text fallback with curated direct answers for common dental questions.

**Error-tolerant integrations**
`services/front_desk.py` — `process_accept` never raises; each client degrades missing config to `dry_run` and failures to an `error` line in the chat block. The accept turn always succeeds.

**Zero third-party HTTP dependencies in the backend clients**
`services/llm.py`, `airtable.py`, `calcom.py`, `resend_email.py` — Built on `urllib.request`. No `httpx`, no `aiohttp`. Retry with exponential backoff on the LLM client.

**Secure authentication**
`frontend/app/api/auth/` — Credentials never in client JS. `httpOnly` cookie with HMAC-SHA256 token. Constant-time comparison prevents timing attacks. Artificial 150ms delay on failed login limits brute-force speed. The chat/reset proxies require the cookie.

---

## 5. Weaknesses & Known Gaps

**W1 — CORS defaults to localhost only — must be configured for production**
`main.py` `_CORS_ORIGINS` — The default (`http://localhost:3000,http://localhost:3001`) is correct for local dev but must be updated via `ALLOWED_ORIGINS` env var before any public deployment.
*Fix:* Set `ALLOWED_ORIGINS=https://your-production-domain.com` in the deployment environment.

**W2 — SSE streaming is simulated for deterministic responses**
`main.py` `event_stream` — Field prompts, validation errors, and estimate presentations don't go through the LLM, so they're word-tokenized with 5ms delays. This is fine UX-wise (messages are short) but it's not "real" streaming for those paths.
*Fix:* This is a UX trade-off, not a bug. No action needed unless fine-grained control is required.

**W3 — In-memory checkpointer**
`graph.py` — `MemorySaver` loses all sessions on restart, and multiple workers can't share state.
*Fix:* Swap in a persistent LangGraph checkpointer (Redis/Postgres) before multi-instance deployment.

**W4 — No rate limiting on `/debug` endpoint**
`main.py` `debug()` — The diagnostic endpoint is unprotected and unauthenticated. It reveals internal KB status and the LLM key prefix.
*Fix:* Add auth middleware or remove from production builds.

**W5 — Session history only saves sessions with an estimate**
`useChat.ts` — History is only persisted when a `visitEstimate` exists. Pure knowledge Q&A sessions are not saved.
*Fix:* Save sessions after any non-trivial exchange (deliberate demo behavior today).

**W6 — No frontend tests**
Zero component tests, no Playwright/Cypress E2E. If a React component breaks, only manual testing will catch it.
*Fix:* Add Playwright smoke tests for the login flow and the happy-path intake flow.

---

## 6. Security & Reliability

**Auth approach**
Server-side validation via `/api/auth/login`. Credentials in `AUTH_USERNAME` / `AUTH_PASSWORD` server-side env vars — never bundled into client JS. Session managed via `httpOnly; SameSite=Lax` cookie with HMAC-SHA256 token. Constant-time comparison prevents timing attacks. Artificial 150ms delay on failed login limits brute-force speed. `/api/chat` and `/api/reset` reject requests without a valid cookie (intake data is PII).

**Input validation coverage**
Strong. All transactional inputs validated by `_coerce_value` (type + range + allowed values + enum synonyms) before storage, then again by `validate_visit_inputs` before estimation. `ChatRequest` Pydantic model enforces `min_length=1` and `max_length=4000` at the API boundary.

**Error handling strategy**
Layered: LLM failures → formatted chunk text. Retrieval failures → fallback message. Integration failures → `error` line in the front-desk block, turn still succeeds. Graph exceptions → SSE `error` event. Network errors → inline frontend error display.

**What happens when external services fail?**
- OpenRouter down: RAG uses formatted chunk text. Transactional flows work with zero LLM dependency.
- Airtable/Cal.com/Resend down or unconfigured: `dry_run`/`error`/`skipped` results, reported honestly in chat; nothing blocks the accept.
- ChromaDB dimension mismatch: auto-detected and collection rebuilt on startup.

**Rate limiting / abuse prevention**
`slowapi`: 60/min on `/chat`, 20/min on `/reset`, keyed by IP.

**CORS**
Restricted to `ALLOWED_ORIGINS` env var (default: localhost dev origins). No longer open to `*`.

---

## 7. Scalability Assessment

**What breaks first at 10x traffic?**
The synchronous LLM calls. Every RAG request blocks a FastAPI/Uvicorn worker thread for 1-3 seconds waiting for OpenRouter. At 10x concurrent users, the thread pool exhausts. (Intake turns don't touch the LLM, so they scale cheaply.)

**What's the most expensive operation?**
LLM calls to OpenRouter — one round-trip per RAG answer (routing is free and deterministic). Each takes 1-3 seconds on a small model.

**Caching strategy**
Vector index cached in-process (`_INDEX_CACHE`). No response caching — identical questions each trigger a full LLM round-trip. An LRU cache on common RAG queries would cut costs significantly.

**Horizontal scaling**
Requires swapping `MemorySaver` for a persistent LangGraph checkpointer (Redis/Postgres) so multiple backend instances share session state behind a load balancer. Until then, sessions are tied to a single process.

---

## 8. Testing & Observability

**What's tested**
56 tests (45 in `tests/test_backend_integration.py`, 7 in `tests/test_contract_scaffold.py`):
- All three complete intake flows (cleaning, emergency, cosmetic) end-to-end, with exact estimate values asserted
- Mid-flow question interruption and exact resume text, including booking-word questions
- The invalid-input matrix (numeric range, enum, email, phone, free text — `pain_level: -2`, `last_visit_year: 2031`, `"i like dogs"`)
- Service switching, adjust/restart/accept, accept clearing intake state
- Compact multi-field input for all three services
- RAG fallback without LLM, conversation history passed to the LLM
- Front-desk integrations: dry-run block, real payloads via monkeypatched `urllib`, HTTP error degradation, emergency email skip
- Routing as a pure function (explicit routing table, no LLM)
- Rate limiting disabled in fixture via `monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")`; integration env keys scrubbed so tests never touch the network

**What's NOT tested**
- Frontend React components (no component tests, no Playwright/Cypress)
- LLM client retry logic and streaming path against a real API
- Vectorstore embedding pipeline (no similarity quality tests)
- Auth cookie issuance and validation

**How would you know if something breaks in production?**
Structured logging via Python `logging` module at DEBUG/INFO/ERROR. `/health` endpoint for uptime monitoring. `/debug` endpoint shows KB status (with a retrieval probe), LLM reachability, session count, and session backend. `trace_id` per turn (not yet exported to a tracing backend).

---

## 9. If I Had More Time...

**P0 — Critical**
1. **Persistent checkpointer** — Redis/Postgres LangGraph checkpointer so sessions survive restarts and scale horizontally. Effort: 1 day.
2. **Async LLM HTTP** — Switch from `urllib.request` to async `httpx`/`aiohttp` for OpenRouter calls. Eliminates blocking of Uvicorn workers under concurrent load. Effort: 1 day.

**P1 — Important**
3. **Frontend tests** — Playwright smoke tests for login and happy-path intake. Effort: 1 day.
4. **Metrics endpoint** — Prometheus `/metrics` with LLM latency histogram, error rate, intake completion rate by service, integration outcome counts. Effort: 1 day.
5. **Real Cal.com availability** — Query open slots instead of computing the next business day deterministically. Effort: 1 day.

**P2 — Nice to Have**
6. **Visit summary PDF/email** — The `visit_estimate` dict already has all required fields; the visit card already exports JSON/CSV. Effort: 1 day.
7. **Protect `/debug` endpoint** — Add auth check or remove from production builds. Effort: 2 hours.
8. **Per-session rate limiting** — More accurate than per-IP behind shared NAT. Effort: half day.

---

## 10. Demo Walkthrough Script

### Step 1 — Set the stage (30 seconds)
"Ivory is a dental front-desk assistant that handles two modes: answering knowledge-base questions using RAG, and running a guided visit-intake workflow. The key design challenge is that you can interrupt an intake, ask a side question, and the bot brings you back to exactly where you were. The backend is the source of truth for all state — the frontend just renders what it receives."

### Step 2 — Login (15 seconds)
Navigate to `http://localhost:3000`. Log in with the credentials from `frontend/.env.local` (`AUTH_USERNAME` / `AUTH_PASSWORD`).
**Point out:** "Auth is server-side — credentials live in server env vars, never in client JS. The session is managed via an httpOnly cookie, and the chat proxy requires it because intake carries PII."

### Step 3 — Knowledge Mode (60 seconds)
Type: `What does a routine cleaning include?`
**Say:** "The bot retrieves from 12 Markdown documents — grounded in public-domain NIDCR and CDC material — using ChromaDB and sentence-transformers. Tokens stream in real time from OpenRouter's streaming API — no blank gap before the first word."

### Step 4 — Start an intake (30 seconds)
Type: `I'd like to book a cleaning`
**Point to the header chips:** flow chip → "cleaning intake · collect". "The backend is now in transactional mode — a LangGraph state machine tracking which field we're collecting."

### Step 5 — The core demo: interrupt and resume (90 seconds)
Type: `What should I do about a toothache?` (with `?`)
**Say:** "The bot answers via RAG AND re-appends the field prompt at the end — 'Now, back to your cleaning visit intake.' The `current_field` pointer and `collected_data` are completely preserved. This is the key invariant."

Resume: type `Maria Santos`, advance through the intake.

### Step 6 — Complete the intake and accept (2 minutes)
Answer: maria@example.com, 2024, insured, morning. Then type `accept`.
**Say:** "The estimate is deterministic — same inputs always produce the same range. The LLM never touches it. And accept is the only place external integrations fire: Airtable lead, Cal.com booking, Resend email — all dry-run without keys, which is what the 'Front desk actions' block is showing."

### Step 7 — Honest self-assessment (30 seconds)
"The main things I'd address before a real production deployment are a persistent checkpointer — session state is in-memory today — and switching the LLM HTTP client from `urllib.request` to async httpx, so concurrent requests don't block Uvicorn workers. I also haven't added frontend tests yet."

### Known Gotchas
- Include `?` in questions mid-intake or the deterministic router treats them as field responses
- First startup is slow (~3 seconds for model load) — hit `/health` before demoing
- `/debug` shows LLM and KB status if something looks wrong

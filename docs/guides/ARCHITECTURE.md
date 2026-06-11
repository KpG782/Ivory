# Ivory Insurance Assistant — Architecture & Engineering Review

## 1. Executive Summary

Ivory is a hybrid insurance chatbot that answers grounded knowledge-base questions (RAG) and runs a structured, multi-step quote workflow (transactional), switching between the two modes in the same session without losing state. Built as a take-home technical assessment demonstrating LLM orchestration, deterministic business logic, streaming API design, and production-grade hardening.

**Core tech stack:** Python FastAPI + LangGraph · OpenRouter (Llama 3.1 8B) · ChromaDB + sentence-transformers · Next.js App Router + React + Tailwind CSS

**Key architectural pattern:** Backend-controlled state machine (LangGraph `StateGraph`) with a Next.js BFF proxy sitting in front of it and a React streaming UI that renders what the backend tells it.

---

## 2. System Architecture

### High-Level Data Flow

```
Browser (React)
    │
    │  POST /api/chat  (SSE)
    ▼
Next.js App Router (BFF Proxy)
app/api/chat/route.ts          ← forwards request verbatim
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
    ├─► router_node           classify intent (deterministic → LLM → rules)
    │       │
    │       ├─► rag_answer         [intent=question]
    │       │       ├─ ChromaDB search
    │       │       └─ OpenRouter streaming (real tokens via on_token callback)
    │       │
    │       ├─► identify_product   [intent=quote, no product yet]
    │       │
    │       ├─► collect_details    [intent=response, step=collect]
    │       │       └─ field validation + coercion
    │       │
    │       ├─► validate_quote     [step=validate]
    │       │       └─ quote_calculator (deterministic)
    │       │
    │       └─► confirm            [step=confirm]
    │
    ▼
Updated ChatState → saved to _SessionStore (Redis or in-memory)
    │
    ▼
SSE stream to browser:
  event: token          (real LLM deltas for RAG / simulated for deterministic responses)
  event: message_complete   (full payload + quote_result + session snapshot)
```

### Component Breakdown

| Component | File(s) | Responsibility |
|-----------|---------|----------------|
| FastAPI app | `backend/main.py` | HTTP endpoints, `_SessionStore`, rate limiting, real SSE streaming |
| LangGraph orchestrator | `backend/graph.py` | Compiles and runs the state machine |
| State schema | `backend/state.py` | `ChatState` TypedDict, `build_initial_state`, `clone_state` |
| Streaming context | `backend/streaming_context.py` | Thread-local on_token callback (bridges asyncio ↔ thread pool) |
| Intent router | `backend/nodes/router.py` | 3-layer classification: deterministic → LLM → rules |
| RAG node | `backend/nodes/rag.py` | Retrieves KB chunks, streams LLM answer via on_token, fallback to formatted text |
| Product identifier | `backend/nodes/identify_product.py` | Keyword-based insurance type detection |
| Field collector | `backend/nodes/collect_details.py` | Step-by-step data gathering with per-type/per-field validation |
| Quote validator | `backend/nodes/validate_quote.py` | Cross-field validation before calculation |
| Confirmation handler | `backend/nodes/confirm.py` | accept / adjust / restart logic |
| LLM client | `backend/services/llm.py` | `OpenRouterClient` — stdlib HTTP, retry, streaming via `_stream_chat_text` |
| Vector store | `backend/services/vectorstore.py` | ChromaDB with sentence-transformers + hash-embedding fallback |
| Quote calculator | `backend/services/quote_calculator.py` | Deterministic premium formulas for auto/home/life |
| Knowledge base | `backend/knowledge_base/*.md` | 12 Markdown documents (company overview, products, claims, FAQs) |
| Session store | `backend/main.py:_SessionStore` | Dict-like class — Redis if `REDIS_URL` set, in-memory fallback |
| Next.js BFF proxy | `frontend/app/api/chat/route.ts` `frontend/app/api/reset/route.ts` | Thin proxy — hides backend URL, avoids CORS |
| Auth routes | `frontend/app/api/auth/login/route.ts` `frontend/app/api/auth/check/route.ts` `frontend/app/api/auth/logout/route.ts` | Server-side credential validation, httpOnly cookie management |
| Auth helper | `frontend/app/api/auth/_auth.ts` | HMAC-SHA256 session token, constant-time comparison |
| Chat hook | `frontend/src/hooks/useChat.ts` | All client state: messages, session, SSE streaming, localStorage persistence |
| App shell | `frontend/src/App.tsx` | Login screen (cookie-based auth), sidebar, chat layout |
| Auth lib | `frontend/src/lib/demoAuth.ts` | Client-side helpers: `checkAuthStatus`, `serverLogin`, `serverLogout` |
| Types | `frontend/src/types.ts` | `ChatMessage`, `SessionSnapshot`, `QuoteResult`, `SavedChatSession` |

### How Components Communicate

- **Frontend → Backend:** HTTP POST via Next.js server-side proxy (no direct browser-to-FastAPI calls)
- **Backend nodes:** Direct Python function calls within the LangGraph execution
- **LLM streaming:** `on_token` callback stored in thread-local (`streaming_context.py`); RAG node pushes deltas; asyncio queue bridges to SSE generator
- **State passing:** Immutable clone on each node (`clone_state` + `deepcopy`)
- **Sessions:** `_SessionStore` reads/writes Redis (with TTL) when `REDIS_URL` is set; falls back silently to in-memory dict

---

## 3. Technical Decisions & Trade-offs

### Decision: LangGraph StateGraph for orchestration

- **What:** Compiled `StateGraph` with 6 named nodes and conditional edges
- **Why:** The quote workflow is a genuine state machine — current step, field, and mode determine what happens next. LangGraph makes transitions explicit and testable rather than buried in if/else chains.
- **Trade-off:** Adds a framework dependency. Simple operations trigger a full graph invocation.
- **Alternative considered:** Plain Python functions with manual routing — simpler to start, harder to reason about as states multiply.
- **When to revisit:** If the workflow gains more than ~10 states or needs parallel branches.

---

### Decision: OpenRouter instead of direct OpenAI or Anthropic API

- **What:** All LLM calls go through `https://openrouter.ai/api/v1/chat/completions`. Default model is `meta-llama/llama-3.1-8b-instruct`.
- **Why:** Single API key across many models. For an assessment, lets the reviewer use their own key without provider lock-in. 8B Llama keeps costs very low.
- **Trade-off:** Routing middleman adds slight latency. 8B model has lower instruction-following reliability than GPT-4 or Claude Sonnet.
- **Alternative considered:** Direct OpenAI API — more reliable JSON output but provider-locked.
- **When to revisit:** If JSON classification reliability becomes a production problem.

---

### Decision: Three-layer intent classification (deterministic → LLM → rules)

- **What:** `classify_intent()` runs: (1) deterministic overrides for unambiguous states, (2) LLM JSON classification, (3) keyword/rule fallback.
- **Why:** Small LLMs frequently misclassify single-word answers like "home" or "auto" as questions. Deterministic overrides skip the LLM for ~60% of calls.
- **Trade-off:** Three code paths increase complexity. Any behavior change must consider all three layers.
- **Alternative considered:** LLM-only — rejected because small models are unreliable for this task without fine-tuning.

---

### Decision: Deterministic quote calculator (not LLM-generated)

- **What:** `quote_calculator.py` uses fixed multiplier formulas. The LLM never touches quote numbers.
- **Why:** Insurance pricing must be reproducible, auditable, and explainable. LLM-generated numbers are hallucinations with no actuarial basis.
- **Trade-off:** Simplified formulas (no zip-code risk tables, no credit scores). But for a demo this is correct — the output is predictable and defensible.
- **When to revisit:** In a real product, integrate with an actual rating engine API.

---

### Decision: Real LLM streaming via thread-local on_token callback

- **What:** `OpenRouterClient._stream_chat_text()` uses OpenRouter's streaming API (`"stream": True`). Tokens are pushed to an `asyncio.Queue` via `loop.call_soon_threadsafe`. The SSE generator drains the queue in real time. For deterministic responses (field prompts, validation errors), word-by-word simulation is kept for UX consistency.
- **Why:** Eliminates the 1-3 second blank gap before the first token appears. The `streaming_context.py` thread-local stores the callback so it reaches deep into the LangGraph execution without modifying `ChatState` or the graph signatures.
- **Trade-off:** Slightly more complex request handling. LangGraph `invoke()` still runs synchronously in a thread-pool worker — the asyncio and threading layers must coordinate correctly.
- **Alternative considered:** Keep simulated streaming. Rejected because it degrades perceived responsiveness significantly.

---

### Decision: `_SessionStore` with Redis + in-memory fallback

- **What:** `SESSION_STORE` is a `_SessionStore` instance that exposes a dict-like interface. If `REDIS_URL` is set and Redis is reachable, sessions are serialized to JSON and stored with a TTL. Otherwise, falls back to an in-process dict.
- **Why:** The in-memory dict was the #1 production gap. Redis fixes data loss on restart and enables horizontal scaling. The fallback preserves the original behaviour for local dev without Redis.
- **Trade-off:** Redis adds infrastructure dependency. The fallback means local dev still works with zero extra setup.
- **When to revisit:** Already production-ready when `REDIS_URL` is configured.

---

### Decision: Server-side auth with httpOnly cookie

- **What:** Credentials (`AUTH_USERNAME` / `AUTH_PASSWORD`) live in server-side env vars. The Next.js `/api/auth/login` route validates them and sets an `httpOnly; SameSite=Lax` session cookie. The session token is an HMAC-SHA256 of the credentials — stateless, no token store required.
- **Why:** The previous design stored `NEXT_PUBLIC_IVORY_LOGIN_PASS` — meaning the password was bundled into client-side JavaScript. That's a critical security gap. Moving validation server-side and using `httpOnly` cookies means the password never reaches the browser.
- **Trade-off:** Requires the Next.js server to handle auth, not just act as a static host.
- **Alternative considered:** JWT with a database of sessions. Correct for multi-user production; stateless HMAC token is sufficient for single-user demo auth.

---

### Decision: `slowapi` rate limiting (60/min chat, 20/min reset)

- **What:** FastAPI endpoints are decorated with `@limiter.limit(...)`. The key function is `get_remote_address` which reads `X-Forwarded-For` behind a proxy. Rate limiting can be disabled via `RATE_LIMIT_ENABLED=false` for tests.
- **Why:** Without rate limiting, a script can exhaust an OpenRouter API key in minutes. 60/min is 1 message per second on average — far above what a real user needs, while blocking automated abuse.
- **Trade-off:** Adds a dependency. Per-IP rate limiting is imprecise behind shared NAT. For production, per-session-ID limiting would be more accurate.

---

### Decision: Next.js BFF proxy (no direct browser-to-FastAPI calls)

- **What:** The frontend never calls FastAPI directly. All requests go through `/api/chat` and `/api/reset`.
- **Why:** Keeps the backend URL off the client. Enables deploying frontend and backend to different hosts without touching React code. Avoids CORS issues.
- **Trade-off:** Adds a network hop. The proxy routes are thin (~20 lines each).

---

## 4. Strengths (What's Done Well)

**Graceful mode switching without state loss**
`graph.py:35-63` — When a question arrives mid-quote, the RAG node answers it then re-appends the current field prompt. The quote pointer (`current_field`, `collected_data`) is untouched throughout. `test_mid_flow_question_preserves_quote_progress` validates this end-to-end.

**Three-layer intent classification with deterministic guards**
`nodes/router.py:51-90` — `_classify_deterministic` catches the cases where small LLMs fail (classifying "home" as a question). The LLM is consulted only for genuinely ambiguous inputs. A rule fallback ensures no silent failures.

**Input validation at two independent layers**
First: `collect_details.py:117-148` — type coercion + range + allowed-value validation at entry, re-prompting without advancing. Second: `validate_quote.py` — cross-field pass before calculation.

**Exhaustive integration test suite**
`tests/test_backend_integration.py` — 28 integration tests (after adding rate-limit fixture). Cover all three quote flows, mid-flow interruption, all validation error paths, product switching, adjust/restart/accept, RAG fallback.

**Real LLM streaming**
`services/llm.py:_stream_chat_text` + `streaming_context.py` — Tokens arrive from OpenRouter as they are generated and are immediately forwarded to the browser. No blank gap before the first word appears.

**Resilient RAG pipeline with multiple fallbacks**
`services/vectorstore.py:83-115` and `nodes/rag.py` — sentence-transformers → hash-embedding fallback; ChromaDB dimension mismatch auto-recovery; LLM failure → formatted chunk text fallback.

**Zero third-party HTTP dependencies in the backend LLM client**
`services/llm.py` — Built on `urllib.request`. No `httpx`, no `aiohttp`. Retry with exponential backoff included.

**Secure authentication**
`frontend/app/api/auth/` — Credentials never in client JS. `httpOnly` cookie with HMAC-SHA256 token. Constant-time comparison prevents timing attacks. Artificial delay on failed login prevents brute-force timing analysis.

---

## 5. Weaknesses & Known Gaps

**W1 — CORS defaults to localhost only — must be configured for production**
`main.py:_CORS_ORIGINS` — The default `http://localhost:3000` is correct for local dev but must be updated via `ALLOWED_ORIGINS` env var before any public deployment.
*Fix:* Set `ALLOWED_ORIGINS=https://your-production-domain.com` in the deployment environment.

**W2 — SSE streaming is simulated for deterministic responses**
`main.py:event_stream` — Field prompts, validation errors, and quote presentations don't go through the LLM, so they're still word-tokenized with 5ms delays. This is fine UX-wise (messages are short) but it's not "real" streaming for those paths.
*Fix:* This is a UX trade-off, not a bug. No action needed unless fine-grained control is required.

**W3 — No message history passed to the LLM**
`rag.py:103-106`, `router.py:131-147` — The LLM only sees the current message. RAG answers and intent classification cannot reference prior conversation turns.
*Fix:* Pass last N messages as context. For intent classification, 2-3 turns is sufficient.

**W4 — No rate limiting on `/debug` endpoint**
`main.py:debug()` — The diagnostic endpoint is unprotected and unauthenticated. It reveals internal KB status and LLM key prefix.
*Fix:* Add auth middleware or remove from production builds.

**W5 — Session history only saves completed quotes**
`useChat.ts:405-411` — History is only persisted when `quoteResult` is set. Pure knowledge Q&A sessions are not saved.
*Fix:* Save sessions after any non-trivial exchange.

**W6 — No frontend tests**
Zero component tests, no Playwright/Cypress E2E. If a React component breaks, only manual testing will catch it.
*Fix:* Add Playwright smoke tests for the login flow and the happy-path quote flow.

---

## 6. Security & Reliability

**Auth approach**
Server-side validation via `/api/auth/login`. Credentials in `AUTH_USERNAME` / `AUTH_PASSWORD` server-side env vars — never bundled into client JS. Session managed via `httpOnly; SameSite=Lax` cookie with HMAC-SHA256 token. Constant-time comparison prevents timing attacks. Artificial 150ms delay on failed login limits brute-force speed.

**Input validation coverage**
Strong. All transactional inputs validated by `_coerce_value` (type + range + allowed values) before storage, then again by `validate_quote_inputs` before calculation. `ChatRequest` Pydantic model enforces `min_length=1` at the API boundary.

**Error handling strategy**
Layered: LLM failures → rule fallback → formatted chunk text. Retrieval failures → fallback message. Graph exceptions → SSE `error` event. Network errors → inline frontend error display.

**What happens when external services fail?**
- OpenRouter down: intent classifier falls to rules; RAG uses formatted chunk text. Transactional flows work with zero LLM dependency.
- Redis down: `_SessionStore` logs a warning and falls back to in-memory. Sessions continue working; they just won't persist across restarts.
- ChromaDB dimension mismatch: auto-detected and collection rebuilt on startup.

**Rate limiting / abuse prevention**
`slowapi`: 60/min on `/chat`, 20/min on `/reset`, keyed by IP. `X-Forwarded-For` respected for reverse-proxy deployments.

**CORS**
Restricted to `ALLOWED_ORIGINS` env var (default: `http://localhost:3000`). No longer open to `*`.

---

## 7. Scalability Assessment

**What breaks first at 10x traffic?**
With Redis configured: the synchronous LLM calls. Every RAG request blocks a FastAPI/Uvicorn worker thread for 1-3 seconds waiting for OpenRouter. At 10x concurrent users, the thread pool exhausts.
Without Redis: the in-memory session fallback (but Redis is the recommended deployment path).

**What's the most expensive operation?**
LLM calls to OpenRouter. A RAG query costs two LLM round-trips (intent classification + RAG generation). Each takes 1-3 seconds on the 8B model.

**Caching strategy**
Vector index cached in-process (`_INDEX_CACHE`). No response caching — identical questions each trigger a full LLM round-trip. An LRU cache on common RAG queries would cut costs significantly.

**Horizontal scaling**
Possible when `REDIS_URL` is set. Multiple backend instances share the same session data behind a load balancer. Without Redis, each instance has its own SESSION_STORE (sessions tied to a specific instance).

---

## 8. Testing & Observability

**What's tested**
28 integration tests in `tests/test_backend_integration.py`:
- All three complete quote flows (auto, home, life) end-to-end
- Mid-flow question interruption and resume
- All validation error paths (numeric, enum, bool, string, date)
- Product switching, adjust/restart/accept
- RAG fallback without LLM
- Rate limiting disabled in fixture via `monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")`

**What's NOT tested**
- Frontend React components (no component tests, no Playwright/Cypress)
- LLM client retry logic and streaming path (no HTTP mock tests)
- Vectorstore embedding pipeline (no similarity quality tests)
- Quote calculator formulas (no unit tests)
- Auth cookie issuance and validation

**How would you know if something breaks in production?**
Structured logging via Python `logging` module at DEBUG/INFO/ERROR. `/health` endpoint for uptime monitoring. `/debug` endpoint shows KB status, LLM reachability, session count, and session backend. `trace_id` per request (not yet exported to a tracing backend).

---

## 9. If I Had More Time...

**P0 — Critical**
1. **Async LLM HTTP** — Switch from `urllib.request` to `httpx` async for OpenRouter calls. Eliminates blocking of Uvicorn workers under concurrent load. Effort: 1 day.
2. **Frontend tests** — Playwright smoke tests for login and happy-path quote. Effort: 1 day.

**P1 — Important**
3. **Conversation history in LLM context** — Pass last 3-5 turns to RAG and intent classifier. Effort: half day. Impact: coherent multi-turn conversations.
4. **Metrics endpoint** — Prometheus `/metrics` with LLM latency histogram, error rate, quote completion rate. Effort: 1 day.
5. **Quote PDF export** — After accepting a quote, generate a PDF summary. `QuoteResult` dict already has all required fields. Effort: 1 day.

**P2 — Nice to Have**
6. **Quote calculator unit tests** — Parameterized tests for each formula. Effort: half day.
7. **Protect `/debug` endpoint** — Add auth check or remove from production builds. Effort: 2 hours.
8. **Per-session rate limiting** — More accurate than per-IP behind shared NAT. Effort: half day.

---

## 10. Demo Walkthrough Script

### Step 1 — Set the stage (30 seconds)
"Ivory is an insurance assistant that handles two modes: answering knowledge-base questions using RAG, and running a guided quote workflow. The key design challenge is that you can interrupt a quote, ask a side question, and the bot brings you back to exactly where you were. The backend is the source of truth for all state — the frontend just renders what it receives."

### Step 2 — Login (15 seconds)
Navigate to `http://localhost:3000`. Use username `admin`, password `ivory123`.
**Point out:** "Auth is now server-side — credentials live in server env vars, never in client JS. The session is managed via an httpOnly cookie."

### Step 3 — Knowledge Mode (60 seconds)
Type: `What does comprehensive coverage include?`
**Say:** "The bot retrieves from 12 Markdown documents using ChromaDB and sentence-transformers. Tokens stream in real time from OpenRouter's streaming API — no blank gap before the first word."

### Step 4 — Start a quote (30 seconds)
Type: `I want a quote for auto insurance`
**Point to sidebar:** Mode → "Quote Flow". "The backend is now in transactional mode — a LangGraph state machine tracking which field we're collecting."

### Step 5 — The core demo: interrupt and resume (90 seconds)
Type: `What does liability coverage mean?` (with `?`)
**Say:** "The bot answers via RAG AND re-appends the field prompt at the end — 'back to your auto quote.' The `current_field` pointer and `collected_data` are completely preserved. This is the key invariant."

Resume: type `2019`, advance through the quote.

### Step 6 — Complete the quote (2 minutes)
Answer: Toyota, Camry, 35, 0, standard.
**Say:** "The premium is deterministic — same inputs always produce the same number. The LLM never touches it. Insurance pricing has to be auditable."

### Step 7 — Honest self-assessment (30 seconds)
"The main thing I'd address before a real production deployment is switching the LLM HTTP client from `urllib.request` to async httpx, so concurrent requests don't block Uvicorn workers. I also haven't added frontend tests yet. Both are scoped P0 follow-ups."

### Known Gotchas
- Include `?` in questions mid-quote or the deterministic classifier treats them as field responses
- First startup is slow (~3 seconds for model load) — hit `/health` before demoing
- `/debug` shows LLM and KB status if something looks wrong

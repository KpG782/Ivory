# Ivory — Interview Q&A Prep

Anticipated questions and strong answers, grounded in the actual codebase.

---

## Architecture & Design

---

**Q: Walk me through the request lifecycle — what happens when a user sends a message?**

**TL;DR:** Browser → Next.js proxy → FastAPI → LangGraph state machine → SSE stream back.

**Full Answer:** The user types a message and it hits `/api/chat` on the Next.js server (`frontend/app/api/chat/route.ts`). That route is a thin proxy — it forwards the request verbatim to the FastAPI backend at `http://127.0.0.1:8000/chat` (or `BACKEND_API_BASE_URL` in production). The FastAPI `/chat` handler (`main.py:136`) looks up or creates a `ChatState` for that `session_id` in the in-memory `SESSION_STORE`, appends the user message, and calls `run_graph(state, message)`. Inside the LangGraph `StateGraph`, the message goes to the `router` node first, which classifies the intent (deterministic overrides first, then LLM, then keyword rules). Based on the intent and current state (mode, quote_step, current_field), it routes to one of: `rag_answer`, `identify_product`, `collect_details`, `validate_quote`, or `confirm`. The updated state is returned, saved back to the session store, and the assistant's response is streamed back as Server-Sent Events — first word-by-word `token` events, then a final `message_complete` event carrying the full message, quote result, and session snapshot.

**Code Reference:** `main.py:136-171`, `graph.py:163-172`, `nodes/router.py:39-48`

**Gotcha to Avoid:** Don't say "the LLM decides everything." Emphasize that the LLM is only consulted for intent classification when the answer is ambiguous, and that quote logic is entirely deterministic.

---

**Q: Why did you choose LangGraph for orchestration?**

**TL;DR:** The quote workflow is a genuine state machine — LangGraph makes the transitions explicit, not implicit.

**Full Answer:** The core challenge is that the same session can be in completely different states: answering a question, waiting for vehicle year, waiting for driver age, showing a quote for confirmation. A plain request/response handler would need a tangled chain of if/else to manage those transitions. LangGraph's `StateGraph` lets me define each state as a named node and each transition as a conditional edge. The entire state machine is visible in ~50 lines of `graph.py`. More importantly, it made testing tractable — I can inject a state, run the graph, and assert on the resulting state without mocking the entire application. The compile-once/run-many pattern also means the graph is validated at startup, not at runtime.

**Code Reference:** `graph.py:109-157`

**Gotcha to Avoid:** Don't oversell it. Acknowledge the trade-off: it adds a dependency and a learning curve. A vanilla Python state machine would also have worked — LangGraph was chosen because it makes the transitions auditable.

---

**Q: How does mode switching work — how does a question mid-quote not break the quote flow?**

**TL;DR:** The question is answered by RAG, then the bot re-appends the current field prompt to the RAG response so the user is guided back.

**Full Answer:** When the router detects `intent=question` while `mode=transactional`, it stores the question in `pending_question` on the state (`graph.py:35-37`) and routes to the RAG node. After the RAG answer is generated, `_rag_node` checks if we're still in `collect` step with a `current_field` set, and if so appends `"\n\nNow, back to your {type} quote — {field_prompt}"` to the end of the RAG response (`graph.py:52-55`). Crucially, the `current_field` and `collected_data` are preserved throughout — the RAG node doesn't touch them. The test `test_mid_flow_question_preserves_quote_progress` verifies this exact behavior end-to-end.

**Code Reference:** `graph.py:35-63`, `tests/test_backend_integration.py:197-226`

**Gotcha to Avoid:** Don't say the frontend manages the resumption. The backend does — the frontend just renders what it receives.

---

**Q: What would you change if you were starting over?**

**TL;DR:** I'd ship all five of the production-readiness fixes from day one rather than retrofitting them.

**Full Answer:** All the major gaps I originally built as deliberate scope cuts are now fixed: Redis-backed session store with in-memory fallback, real OpenRouter streaming via thread-local callback into an asyncio queue, server-side httpOnly cookie auth with HMAC-SHA256 tokens, restricted CORS via `ALLOWED_ORIGINS` env var, and `slowapi` rate limiting on `/chat` and `/reset`. If starting over, I'd wire those in from the beginning — the retrofits were straightforward, but they touched a lot of files simultaneously. The one structural change that wasn't retrofitted is making LLM calls async end-to-end using `aiohttp` instead of `urllib.request`. Right now LangGraph runs in a thread-pool executor (`run_in_executor`), which bridges asyncio and the sync LLM client. That works, but fully async HTTP would be cleaner and scale better under concurrency.

**Code Reference:** `main.py` (_SessionStore, rate limiter, CORS), `streaming_context.py`, `services/llm.py` (_stream_chat_text)

**Gotcha to Avoid:** Don't present the gaps as still open. They were fixed — explain what each fix involved, then point to what genuinely remains (async LLM HTTP).

---

**Q: How would this scale to 10x or 100x users?**

**TL;DR:** Session persistence is solved; the synchronous LLM HTTP client is the next bottleneck.

**Full Answer:** The in-memory session store is no longer the scaling bottleneck — `_SessionStore` in `main.py` now uses Redis when `REDIS_URL` is set, with in-memory as fallback. That unlocks horizontal Uvicorn workers and load balancers since session state lives in Redis, not process memory. Rate limiting via `slowapi` (60/min chat, 20/min reset) is also in place, so malicious clients can't exhaust memory with fake sessions. At 100x, the bottleneck shifts to the synchronous LLM calls in `services/llm.py` — every request that needs the LLM blocks a thread for 1-3 seconds using `urllib.request`. The fix is switching to `aiohttp` for truly async HTTP, which would let FastAPI's event loop handle many concurrent requests without thread-pool exhaustion. For RAG-heavy workloads, an LRU cache on common queries ("what does comprehensive cover?") would cut LLM calls further.

**Code Reference:** `main.py` (_SessionStore, rate limiter), `services/llm.py:79-107`

**Gotcha to Avoid:** Don't say the session store is still a problem — it's fixed. Lead with what the new bottleneck actually is (async LLM HTTP).

---

**Q: What's the most complex part of the system?**

**TL;DR:** The three-layer intent classifier and the collect/validate cycle that prevents malformed data from advancing the state machine.

**Full Answer:** The most complex behavior is the interaction between intent classification and field collection. When a user is mid-quote and types something like "what does liability mean?", the system must decide: is this a question to answer with RAG, or a field response to parse? A small LLM will frequently get this wrong. The solution is a three-layer classifier (`nodes/router.py`): first check deterministic rules (if `current_field` is set and the message has no `?` and no question words, it's a field response), then try the LLM, then fall back to keyword rules. Getting that cascade right — and testing all the edge cases — took significant iteration. The input validation in `collect_details.py` is also non-trivial: it handles type coercion, range validation, allowed-value matching, and a special multi-field parser for auto insurance where a user might type "2019 Toyota Camry" all at once.

**Code Reference:** `nodes/router.py:51-90`, `nodes/collect_details.py:243-339`

**Gotcha to Avoid:** Don't say "it's all complex." Pick the genuinely hardest problem and explain it concretely.

---

## Code Quality & Engineering

---

**Q: How do you handle errors?**

**TL;DR:** Layered degradation — every failure has a fallback that keeps the bot operational.

**Full Answer:** Each layer has its own error handling. LLM failures in the intent classifier fall back to rule-based classification (`router.py:148`). LLM failures in RAG fall back to formatted text from the retrieved chunks (`rag.py:113-122`). If ChromaDB has a dimension mismatch at startup, the collection is auto-deleted and rebuilt (`vectorstore.py:252-268`). At the API level, if `run_graph` throws an unhandled exception, it's caught in `main.py:142-146` and returned as an SSE `error` event rather than a 500. On the frontend, `useChat.ts:550-563` catches network errors and displays them inline. The core principle is: no user-facing blank screen from an infrastructure failure.

**Code Reference:** `main.py:142-146`, `rag.py:91-122`, `vectorstore.py:252-268`

**Gotcha to Avoid:** Don't claim all errors are handled. The `json.loads` in `chat_json()` is now wrapped in a try/except (fixed), but the broader point stands — acknowledge that error handling is layered degradation, not exhaustive coverage.

---

**Q: What's your testing strategy?**

**TL;DR:** Integration tests over the full FastAPI + LangGraph stack with the LLM and RAG monkeypatched.

**Full Answer:** The 22 integration tests in `tests/test_backend_integration.py` exercise the full stack from HTTP request to SSE response, using FastAPI's `TestClient`. The LLM classifier is monkeypatched to return `None` (forcing the rule fallback), and the RAG retrieval is replaced with a fixed stub response. This makes tests fast (~2 seconds for the full suite) and deterministic. The tests cover every quote flow end-to-end, all validation error paths for every field type, the RAG fallback path, mid-flow interruption and resumption, and all confirmation actions. There are no unit tests for individual nodes or services — the integration tests implicitly cover them. There are no frontend tests.

**Code Reference:** `tests/test_backend_integration.py:48-78`

**Gotcha to Avoid:** Don't oversell coverage. Acknowledge what's not tested: the quote calculator formulas, the LLM client retry logic, the vectorstore embedding pipeline, and all frontend behavior.

---

**Q: How do you validate inputs?**

**TL;DR:** Two independent layers: coerce-and-validate at collection time, then re-validate before calculation.

**Full Answer:** The first layer is in `collect_details.py`'s `_coerce_value` function. As each field answer arrives, it's coerced to the target type (int, float, bool, str), checked against min/max range, and matched against an allowed-values list. If it fails, a human-readable error message is generated and the same field is re-prompted — the pointer doesn't advance. There's also a `_clean_text_value` function for string fields that catches off-topic answers, policy questions embedded in answers, and a location denylist. The second layer runs in `validate_quote.py` before the quote calculator is called — it re-validates all collected fields as a coherent set. This belt-and-suspenders approach means even if a bug in the first layer lets bad data through, the calculator never receives invalid inputs.

**Code Reference:** `nodes/collect_details.py:243-339`, `services/quote_calculator.py:18-117`

**Gotcha to Avoid:** Don't forget to mention the `ChatRequest` Pydantic model at the API boundary (`main.py:30-31`) — that's the first validation layer at the HTTP level.

---

**Q: Show me code you're most proud of and why.**

**TL;DR:** The `_classify_deterministic` function — it's the most carefully engineered piece of the system.

**Full Answer:** I'd point to `_classify_deterministic` in `nodes/router.py:51-90`. The problem it solves is real: a small 8B LLM frequently classifies single-word answers like "home", "auto", or "2019" as questions when they appear without context. Without this guard, the entire quote flow breaks for users who give short, direct answers. The function encodes the insight that in certain states, the classification is unambiguous — if `current_field` is set, the message has no `?`, and no question words appear, it's a field response, full stop. It also handles the edge case where a user in the `identify` step types a product keyword, which should always be classified as a response regardless of what the LLM thinks. It's compact (~40 lines), thoroughly tested, and solves a real problem that would otherwise surface in demos.

**Code Reference:** `nodes/router.py:51-90`

**Gotcha to Avoid:** Don't just say "I'm proud of all of it." Pick one thing, explain the problem it solves, and explain why the implementation is good.

---

**Q: Show me code you'd refactor if you had time.**

**TL;DR:** The synchronous `urllib.request` LLM client — it blocks threads under concurrency.

**Full Answer:** `services/llm.py`'s `_stream_chat_text` and `_call_api` use `urllib.request.urlopen`, which is blocking. Every concurrent LLM call occupies a thread-pool worker for 1-3 seconds. For the demo volume this is fine, but it's the right thing to replace. I'd switch to `aiohttp` and make the LLM client fully async — `async def chat_text(...)` returning an async generator. That would eliminate the `run_in_executor` wrapper in `main.py` and let FastAPI's event loop handle many concurrent streams without thread exhaustion. The `chat_json` method also had an unhandled `json.loads` — that's been fixed with a try/except that returns `None` on parse failure and logs the raw content for debugging.

**Code Reference:** `services/llm.py` (_call_api, _stream_chat_text), `main.py` (run_in_executor usage)

**Gotcha to Avoid:** Don't say `json.loads` is still unhandled — it's been fixed. Pick the actual remaining issue (sync HTTP).

---

## AI/LLM-Specific Questions

---

**Q: Why this model and provider? Why Llama 3.1 8B via OpenRouter?**

**TL;DR:** OpenRouter for flexibility; 8B model to keep costs low for a demo where quality requirements are modest.

**Full Answer:** OpenRouter lets the reviewer use their own API key without being locked to one provider, and lets me swap the model via an env var without touching code. The 8B Llama model is cheap — at ~$0.10 per million input tokens, a full demo session costs fractions of a cent. For this application, the LLM has two jobs: classify intent (a 3-class classification with context) and answer insurance questions from retrieved context. Both tasks are well within the 8B model's capabilities, especially because the intent classifier has a deterministic override and a rule fallback that handle the cases where the LLM fails. If I needed more reliable JSON output or better reasoning on edge cases, I'd switch to a larger model (Llama 3.1 70B or Mistral Nemo) via the same OpenRouter API, with no code changes.

**Code Reference:** `services/llm.py:16-17`, `env.example`

**Gotcha to Avoid:** Don't apologize for using a small model. Explain why it's sufficient for the task and what you'd change if quality requirements increased.

---

**Q: How do you handle hallucinations?**

**TL;DR:** The system prompt constrains the LLM to answer only from context, and quote numbers never come from the LLM.

**Full Answer:** Two mechanisms. First, the RAG system prompt (`rag.py:12-17`) explicitly tells the LLM: "Answer only using the provided knowledge base context. If the context is insufficient, say so plainly and do not invent policy details." This doesn't eliminate hallucinations entirely, but it significantly reduces the surface area — the LLM is instructed to cite sources and admit gaps. Second, and more importantly, the highest-stakes output — the quote premium — is never generated by the LLM. It's calculated by a deterministic formula in `quote_calculator.py`. The LLM cannot hallucinate a price. The worst hallucination that can happen is in the knowledge Q&A flow, where the fallback message ("I do not have enough context to answer that confidently") is the safe default.

**Code Reference:** `nodes/rag.py:12-17`, `services/quote_calculator.py:120-195`

**Gotcha to Avoid:** Don't claim hallucinations are "solved." The LLM can still fabricate details in the RAG path. Acknowledge the mitigations and their limits.

---

**Q: What's your prompt engineering approach?**

**TL;DR:** Two focused prompts — one for knowledge Q&A (RAG), one for intent classification — both with tight constraints.

**Full Answer:** There are two places where prompts are used. The RAG prompt (`rag.py:12-17`) is a system prompt that establishes persona ("Ivory insurance assistant"), scope constraint ("answer only from context"), and a behavior for quote interruptions ("do not reset quote progress"). The user prompt is the question plus the numbered retrieved chunks. The intent classification prompt (`router.py:131-141`) is very minimal: classify into exactly one of three values, return JSON with a single key. I deliberately kept both prompts short — long, complex prompts increase token costs and give the 8B model more ways to go off-script. The most important prompt engineering decision was not adding more instructions, but instead building the deterministic overrides that eliminate the need for the LLM on ~60% of classification calls.

**Code Reference:** `nodes/rag.py:12-17`, `nodes/router.py:131-141`

**Gotcha to Avoid:** Don't say you "optimized" the prompts without specifics. Explain what problem each prompt solves and how you constrained it.

---

**Q: How do you control cost and token usage?**

**TL;DR:** Small model, short prompts, strict `max_tokens`, and deterministic overrides that skip the LLM entirely.

**Full Answer:** Four mechanisms. First, the model is Llama 3.1 8B via OpenRouter — roughly 10x cheaper per token than GPT-4o. Second, the intent classification prompt is extremely short (~50 tokens) and capped at `max_tokens=60` (`router.py:146`). Third, the RAG response is capped at `max_tokens=450` (`rag.py:107`). Fourth — and most impactful — the deterministic classifier overrides mean the LLM is not called at all for ~60% of classification decisions (field responses in a known quote state, product keywords during identify, etc.). For a demo, the total cost per full quote flow (auto, home, or life) is less than $0.01. If costs were a concern at scale, I'd add an LRU cache on common RAG queries — questions like "what does comprehensive cover?" are asked repeatedly and have stable answers.

**Code Reference:** `nodes/router.py:51-90`, `nodes/rag.py:107`, `nodes/router.py:146`

**Gotcha to Avoid:** Don't make up numbers. Use the actual `max_tokens` values from the code.

---

**Q: How would you evaluate output quality?**

**TL;DR:** I don't have a formal eval pipeline — this is an honest gap. Here's what I'd build.

**Full Answer:** Currently there's no automated quality evaluation beyond the integration tests (which check for specific strings, not quality). For a production system, I'd build two evaluation tracks. For RAG answers: a small labeled dataset of (question, expected_answer) pairs with a judge LLM scoring groundedness (is the answer supported by the retrieved context?) and relevance (does it answer the question?). For intent classification: a labeled set of (message + state, expected_intent) pairs — I'd run the classifier against this set after any prompt or model change. For the quote flow, the deterministic calculator is easy to evaluate: I have unit tests with known inputs and expected outputs. The hardest thing to evaluate is the mode-switching behavior — whether the bot correctly stays in quote mode versus drifting to conversational mode — which is why the integration tests cover that path exhaustively.

**Code Reference:** `tests/test_backend_integration.py:197` (mid-flow test)

**Gotcha to Avoid:** Don't pretend you have an eval pipeline if you don't. Interviewers respect "this is what I'd build" over a fabricated answer.

---

**Q: What happens when the OpenRouter API is down or slow?**

**TL;DR:** The bot stays operational — it falls back to rule-based classification and formatted chunk answers.

**Full Answer:** The LLM client (`services/llm.py:92-107`) has a retry loop with exponential backoff (up to 2 retries, max 4 second delay). If all retries fail, it raises `OpenRouterError`. In the intent classifier (`router.py:148`), this is caught and `None` is returned, which falls through to the rule-based classifier — the bot can still route requests correctly. In the RAG node (`rag.py:113-122`), an LLM failure falls back to `_format_fallback_answer`, which generates a direct text answer from the retrieved chunks without the LLM. The `/debug` endpoint shows LLM reachability status, so a developer can quickly diagnose connectivity issues. During a demo, if OpenRouter is slow, responses will be delayed but correct; if it's completely down, the bot degrades gracefully but quote flows continue working perfectly since the calculator doesn't use the LLM.

**Code Reference:** `services/llm.py:92-107`, `nodes/rag.py:113-122`, `main.py:98-119`

**Gotcha to Avoid:** Demonstrate you've actually tested this scenario — the integration tests monkeypatch the LLM away, which is effectively testing the "LLM unavailable" path.

---

## Trade-offs & Decision Making

---

**Q: How does the real SSE streaming work?**

**TL;DR:** OpenRouter streams tokens → thread-local callback → asyncio queue → SSE generator.

**Full Answer:** The LLM call runs in a thread-pool executor (via `asyncio.run_in_executor`) because LangGraph is synchronous. To bridge that thread to the async FastAPI SSE generator, I use a thread-local `on_token` callback (`streaming_context.py`). Before calling `run_graph`, the SSE handler puts an `asyncio.Queue` reference into thread-local storage. Deep inside the LangGraph execution, `rag.py` calls `get_on_token()` and passes it to `llm.chat_text()`. The LLM client (`services/llm.py:_stream_chat_text`) uses OpenRouter's `"stream": True` API, parses the `data:` SSE lines, and calls `on_token(delta)` on each token. That callback does `loop.call_soon_threadsafe(queue.put_nowait, token)`, putting the token into the asyncio queue. The SSE generator on the main thread drains the queue with `await queue.get()` and yields `token` events to the browser. A sentinel `None` signals completion. If no tokens were emitted (e.g., classification-only flows), it falls back to word-level simulation of the final message.

**Code Reference:** `streaming_context.py`, `main.py` (event_stream, _run_in_thread), `services/llm.py` (_stream_chat_text), `nodes/rag.py` (get_on_token usage)

**Gotcha to Avoid:** Don't say streaming is simulated — it's real token streaming from OpenRouter. The word-simulation fallback only fires when the graph never calls the LLM (e.g., a quote confirmation).

---

**Q: What was the hardest technical decision?**

**TL;DR:** Deciding where to put the state — frontend or backend — and committing fully to backend-controlled state.

**Full Answer:** The hardest architectural decision was making the backend the single source of truth for all state, including the current field, mode, and quote progress. The alternative — storing state in React and sending it with each request — would have simplified the backend but created a split-brain problem: what if the frontend's state diverges from what the backend expects? By having the backend own state completely, the frontend becomes a pure render layer. It receives a `session` snapshot with every SSE `message_complete` event and updates its UI to match. The cost is that the frontend can't optimistically update — it must wait for the backend to confirm a state transition. For a chatbot, this is the right trade-off; the alternative would have caused subtle bugs where the user's UI shows "collecting details" but the backend thinks we're in "confirm."

**Code Reference:** `main.py:188-198` (_public_session_state), `frontend/src/hooks/useChat.ts:511-516`

**Gotcha to Avoid:** Don't say "all decisions were easy." This is a real architectural tension that has concrete implications.

---

**Q: Where did you cut corners and why?**

**TL;DR:** I originally cut five corners to ship fast — and then fixed all five before the final demo.

**Full Answer:** The original version had five deliberate scope cuts: in-memory session store, simulated word-level SSE streaming, `NEXT_PUBLIC_` password exposed in the client bundle, open CORS (`allow_origins=["*"]`), and no rate limiting. I made each tradeoff explicitly to move fast on the core behavior — state machine, RAG, quote calculator. Once the core was solid, I fixed all five: `_SessionStore` now uses Redis when `REDIS_URL` is set; streaming is real OpenRouter tokens via thread-local callback into an asyncio queue; auth is HMAC-SHA256 httpOnly cookie with credentials in server-side env vars only; CORS is restricted to `ALLOWED_ORIGINS`; `slowapi` rate limits `/chat` at 60/min and `/reset` at 20/min. The one genuine remaining tradeoff is the synchronous `urllib.request` LLM client — I'd switch to `aiohttp` in a production hardening pass.

**Code Reference:** `main.py` (_SessionStore, CORS, rate limiter), `streaming_context.py`, `frontend/app/api/auth/`, `services/llm.py`

**Gotcha to Avoid:** Don't present the original five gaps as still open. Explain both why they were originally cut AND that they were fixed, so you demonstrate the full decision arc.

---

**Q: What's the biggest risk in this architecture?**

**TL;DR:** The synchronous LLM client under high concurrency, and the stateless session token model under credential rotation.

**Full Answer:** The in-memory session and open CORS risks are fixed — sessions now persist in Redis (`_SessionStore` with TTL), CORS is locked to `ALLOWED_ORIGINS`, and rate limiting is in place. The remaining risks are: (1) The LLM client uses `urllib.request` (synchronous), so under high concurrency each `/chat` request that hits the LLM blocks a thread for 1-3 seconds. Under heavy load this exhausts the thread pool before the rate limiter can help. (2) The session token is stateless — HMAC-SHA256 of `AUTH_USERNAME:AUTH_PASSWORD` — so there's no way to invalidate individual sessions. Changing the password (`AUTH_PASSWORD`) invalidates all sessions at once. For a demo this is fine; for a multi-user production app you'd want a token store with per-session revocation. (3) The backend has no authentication of its own — requests from any client with a valid `session_id` are accepted. The httpOnly cookie only protects the frontend; the FastAPI API is still open on `localhost:8000`.

**Code Reference:** `services/llm.py:79-107`, `frontend/app/api/auth/_auth.ts` (hmacToken), `main.py` (CORS, rate limiter)

**Gotcha to Avoid:** Don't say the session store or CORS are still risks — they're fixed. Lead with what actually remains.

---

**Q: If you had 2 more weeks, what would you add?**

**TL;DR:** The production-readiness fixes are done — the next two weeks would be feature and observability work.

**Full Answer:** The five production-readiness items (Redis sessions, real streaming, restricted CORS, httpOnly auth, rate limiting) are already shipped. The remaining work I'd prioritize: Week 1: Conversation history in LLM context — right now RAG and intent classification only see the current message, not prior turns. Adding a rolling window of the last 5 messages to the system prompt would improve coherence on multi-turn exchanges. Then async LLM HTTP — replace `urllib.request` with `aiohttp` so the FastAPI event loop handles concurrent LLM requests without thread-pool exhaustion. Week 2: Quote PDF/email export — `QuoteResult` already has all the data, it's just rendering. Add a Prometheus `/metrics` endpoint tracking LLM latency histogram, error rate by endpoint, and quote completion rate by product. Export the `trace_id` (already generated in `main.py:138`) to OpenTelemetry. Add frontend tests — currently there are none.

**Code Reference:** `main.py:138` (trace_id), `services/quote_calculator.py` (complete quote data), `services/llm.py` (urllib.request → aiohttp target)

**Gotcha to Avoid:** Don't list the already-fixed items as future work. Show you know what's shipped and what genuinely remains.

---

## Production & Operations

---

**Q: How would you deploy this?**

**TL;DR:** Backend as a Docker container via docker-compose or Kubernetes; frontend deployed to Vercel or as a Docker container.

**Full Answer:** The backend has a production-ready `Dockerfile` already. It uses `python:3.12-slim`, installs dependencies, copies source, and runs `uvicorn main:app --host 0.0.0.0 --port ${PORT} --proxy-headers`. The `docker-compose.backend.yml` shows the full deployment config: persistent volume for ChromaDB and model weights at `/data`, environment variables for secrets, and a healthcheck that curls `/health`. For the frontend, `next build` + `next start` runs on Node.js — it deploys to Vercel with zero config, or as a Docker container for self-hosted. `BACKEND_API_BASE_URL` environment variable connects the Next.js proxy to wherever the FastAPI backend is running. The backend is already deployed to Docker Hub as `kpg782/ivory-backend:latest`.

**Code Reference:** `backend/Dockerfile`, `docker-compose.backend.yml`, `frontend/app/api/chat/route.ts:4`

**Gotcha to Avoid:** Don't just say "deploy to the cloud." Know the specifics: which ports, which env vars, what the healthcheck does.

---

**Q: How would you monitor this in production?**

**TL;DR:** Currently: structured Python logging + `/health` + `/debug` endpoints. What I'd add: Prometheus metrics + distributed tracing.

**Full Answer:** Right now: `logging.basicConfig(level=logging.DEBUG)` in `main.py:23-26` gives structured logs for every request, LLM call, and retrieval result. The `/health` endpoint returns `{"status": "ok"}` for uptime monitoring. The `/debug` endpoint (`main.py:76-126`) shows KB status, a retrieval probe, LLM reachability, and session count — useful for diagnosing issues without SSH access. What I'd add in production: a Prometheus `/metrics` endpoint tracking LLM latency histogram, error rate by endpoint, quote completion rate by product type, and active session count. I'd also export the `trace_id` (generated at `main.py:138`) to OpenTelemetry so I can trace a request from the browser through Next.js into FastAPI and into the LLM call.

**Code Reference:** `main.py:23-26`, `main.py:68-126`

**Gotcha to Avoid:** Don't say "I'd add Datadog" without explaining what you'd instrument. Be specific about the metrics that matter for this application.

---

**Q: How do you handle secrets and env vars?**

**TL;DR:** Backend secrets in `.env`/shell; frontend credentials in server-side env vars only — nothing sensitive in the client bundle.

**Full Answer:** The backend's `env.py` loads `.env` files from the backend directory and repo root using `python-dotenv` with `override=False` — shell env vars take precedence. In Docker, secrets are injected via `environment:` in `docker-compose.backend.yml`. The only required secret is `OPENROUTER_API_KEY`. On the frontend, `BACKEND_API_BASE_URL` is server-side (no `NEXT_PUBLIC_` prefix), so the backend URL never reaches the browser. Auth credentials (`AUTH_USERNAME`, `AUTH_PASSWORD`) and `SESSION_SECRET` are also server-side env vars in `frontend/.env.local` — they're read by the Next.js API routes (`app/api/auth/`) and never bundled into client JavaScript. The only `NEXT_PUBLIC_` auth var is `NEXT_PUBLIC_AUTH_DEMO_USER`, an optional username hint for the login screen. The password is intentionally not exposed. Previously the password was in `NEXT_PUBLIC_IVORY_LOGIN_PASS` — that's been removed entirely.

**Code Reference:** `backend/env.py`, `frontend/app/api/auth/_auth.ts`, `frontend/src/lib/demoAuth.ts`, `frontend/.env.example`

**Gotcha to Avoid:** Don't mention `NEXT_PUBLIC_IVORY_LOGIN_PASS` as a current issue — it's been removed. Explain how auth was fixed (server-side env vars + httpOnly cookie).

---

**Q: What's your CI/CD strategy?**

**TL;DR:** Currently none. Here's what I'd set up.

**Full Answer:** The project doesn't have CI/CD configured yet — it was built as an assessment. For a production setup: a GitHub Actions workflow that runs `pytest tests/` on every PR (the tests run without any external dependencies since the LLM and RAG are monkeypatched). A `typecheck` step running `tsc --noEmit` for the frontend. On merge to main: build and push the Docker image to Docker Hub (already using `kpg782/ivory-backend`), and trigger a Watchtower pull on the production host (or update the ECS task definition, or ArgoCD sync, depending on the platform). The backend healthcheck in `docker-compose.backend.yml` handles zero-downtime via the `start_period: 45s` grace period for model loading.

**Code Reference:** `pytest.ini`, `frontend/package.json:9`, `docker-compose.backend.yml:18-23`

**Gotcha to Avoid:** Don't claim you have CI/CD if you don't. "Here's what I'd build" is a better answer than a fabricated pipeline.

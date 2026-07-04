# Ivory — Interview Q&A Prep

Anticipated questions and strong answers, grounded in the actual codebase.

---

## Architecture & Design

---

**Q: Walk me through the request lifecycle — what happens when a user sends a message?**

**TL;DR:** Browser → Next.js proxy → FastAPI → LangGraph state machine → SSE stream back.

**Full Answer:** The user types a message and it hits `/api/chat` on the Next.js server (`frontend/app/api/chat/route.ts`). That route validates the httpOnly session cookie (intake carries PII) and then forwards the request verbatim to the FastAPI backend at `http://127.0.0.1:8000/chat` (or `BACKEND_API_BASE_URL` in production). The FastAPI `/chat` handler (`main.py`) runs `graph.run_graph(session_id, message)` in a thread-pool worker: it loads the prior state from the LangGraph checkpointer (keyed by `thread_id == session_id`), appends the user message, and invokes the compiled graph. The `router` node makes one deterministic routing decision (`nodes/router.py` — ordered rules, no LLM) and the conditional edge sends the turn to one of: `rag_answer`, `identify_service`, `collect_details` (which chains into `validate_visit`), or `confirm`. The checkpointer atomically persists the resulting state, and the assistant's response streams back as Server-Sent Events — `token` events first, then a final `message_complete` event carrying the full message, the `visit_estimate`, and a session snapshot.

**Code Reference:** `main.py` (`chat`, `event_stream`), `graph.py` (`run_graph`, `_route_from_router`), `nodes/router.py` (`decide`)

**Gotcha to Avoid:** Don't say "the LLM decides everything." The LLM is never on the control-flow path at all — it only writes RAG answer prose. Routing, validation, and estimation are entirely deterministic.

---

**Q: Why did you choose LangGraph for orchestration?**

**TL;DR:** The intake workflow is a genuine state machine — LangGraph makes the transitions explicit, not implicit.

**Full Answer:** The core challenge is that the same session can be in completely different states: answering a question, waiting for the patient's name, waiting for a pain level, showing an estimate for confirmation. A plain request/response handler would need a tangled chain of if/else to manage those transitions. LangGraph's `StateGraph` lets me define each state as a named node and each transition as a conditional edge. The entire state machine is visible in `_build_graph()` in `graph.py`. It also gives me durable per-session memory for free: the checkpointer is the single source of truth for conversation state, keyed by `thread_id == session_id` — there is no separate hand-rolled session store. And it made testing tractable — I can inject a state, run the graph, and assert on the resulting state without mocking the entire application.

**Code Reference:** `graph.py` (`_build_graph`, `run_graph`, `_checkpointer`)

**Gotcha to Avoid:** Don't oversell it. Acknowledge the trade-off: it adds a dependency and a learning curve. A vanilla Python state machine would also have worked — LangGraph was chosen because it makes the transitions auditable and checkpoints state.

---

**Q: How does mode switching work — how does a question mid-intake not break the intake flow?**

**TL;DR:** The question is answered by RAG, then the bot re-appends the current field prompt to the RAG response so the user is guided back.

**Full Answer:** When the user is mid-intake (`current_field` is set) and the message contains a `?`, the router returns `answer_then_resume` — this rule fires before the booking-word rule, so even "How much does a whitening appointment cost?" is answered rather than hijacking the flow. The turn goes to the RAG node, and after the answer is generated, `_rag_node` checks whether we're still in the `collect` step with a `current_field` set; if so it appends `"\n\nNow, back to your {service label} intake — {field_prompt}"` to the end of the RAG response (`graph.py`). Crucially, `current_field` and `collected_data` are preserved throughout — the RAG node doesn't touch them. The tests `test_mid_flow_question_preserves_intake_progress` and `test_midflow_question_with_booking_word_answers_then_resumes` verify this exact behavior end-to-end.

**Code Reference:** `nodes/router.py` (`decide`, rule P2), `graph.py` (`_rag_node`), `tests/test_backend_integration.py`

**Gotcha to Avoid:** Don't say the frontend manages the resumption. The backend does — the frontend just renders what it receives.

---

**Q: What would you change if you were starting over?**

**TL;DR:** I'd ship the production-readiness fixes from day one rather than retrofitting them.

**Full Answer:** All the major gaps I originally built as deliberate scope cuts are now fixed: conversation state moved into the LangGraph checkpointer as the single source of truth, real OpenRouter streaming via thread-local callback into an asyncio queue, server-side httpOnly cookie auth with HMAC-SHA256 tokens, restricted CORS via `ALLOWED_ORIGINS` env var, and `slowapi` rate limiting on `/chat` and `/reset`. If starting over, I'd wire those in from the beginning — the retrofits were straightforward, but they touched a lot of files simultaneously. Two structural changes weren't retrofitted: the checkpointer is still `MemorySaver` (in-memory, lost on restart — a Redis/Postgres checkpointer is the production step), and LLM calls are synchronous `urllib.request` bridged through a thread-pool executor rather than fully async `aiohttp`.

**Code Reference:** `graph.py` (checkpointer), `streaming_context.py`, `services/llm.py` (`_stream_chat_text`), `main.py` (rate limiter, CORS)

**Gotcha to Avoid:** Don't present the fixed gaps as still open. Explain what each fix involved, then point to what genuinely remains (persistent checkpointer, async LLM HTTP).

---

**Q: How would this scale to 10x or 100x users?**

**TL;DR:** Per-session state is isolated in the checkpointer; the in-memory checkpointer and the synchronous LLM HTTP client are the bottlenecks.

**Full Answer:** Rate limiting via `slowapi` (60/min chat, 20/min reset) is in place, so malicious clients can't exhaust memory with fake sessions. The first scaling step is swapping the in-memory `MemorySaver` checkpointer for a persistent one (Redis or Postgres — LangGraph supports both) so state survives restarts and multiple Uvicorn workers behind a load balancer can share sessions. The second bottleneck is the synchronous LLM calls in `services/llm.py` — every request that needs the LLM blocks a thread for 1-3 seconds using `urllib.request`. The fix is switching to `aiohttp` for truly async HTTP, which would let FastAPI's event loop handle many concurrent requests without thread-pool exhaustion. Notably, intake turns never call the LLM at all — routing, field collection, validation, and estimation are local deterministic logic — so the intake path scales cheaply. For RAG-heavy workloads, an LRU cache on common queries ("what does a routine cleaning include?") would cut LLM calls further.

**Code Reference:** `graph.py` (`MemorySaver`), `main.py` (rate limiter), `services/llm.py`

**Gotcha to Avoid:** Don't say sessions are Redis-backed — they're not. State lives in the LangGraph checkpointer, in memory today; name the persistent checkpointer as the concrete next step.

---

**Q: What's the most complex part of the system?**

**TL;DR:** The deterministic router's rule ordering and the collect/validate cycle that prevents malformed data from advancing the state machine.

**Full Answer:** The most complex behavior is the interaction between routing and field collection. When a user is mid-intake and types something like "How much does a whitening appointment cost?", the system must decide: is this a question to answer with RAG, or a field response to parse, or a request to switch services? An LLM classifier would frequently get this wrong, so the router (`nodes/router.py`) is a pure function of (state, message) with seven ordered rules: restart wins first, then mid-intake questions (a `?` while `current_field` is set) are always answered-then-resumed, then explicit booking words start or switch an intake, then a pending field absorbs the reply, and so on. Getting that ordering right — and testing all the edge cases like "Booker Smith" as a patient name — took real iteration. The input validation in `collect_details.py` is also non-trivial: it handles type coercion, range validation, enum synonym normalization ("out of pocket" → `self_pay`), question-shaped answers ("do you offer implants"), and a multi-field parser that fills several fields from one compact reply like "Maria Santos, maria@example.com, 2024, insured, morning".

**Code Reference:** `nodes/router.py` (`decide`), `nodes/collect_details.py` (`_coerce_value`, `_clean_text_value`, `_merge_sequential_input`)

**Gotcha to Avoid:** Don't say "it's all complex." Pick the genuinely hardest problem and explain it concretely.

---

## Code Quality & Engineering

---

**Q: How do you handle errors?**

**TL;DR:** Layered degradation — every failure has a fallback that keeps the bot operational.

**Full Answer:** Each layer has its own error handling. LLM failures in RAG fall back to formatted text from the retrieved chunks (`rag.py`). Retrieval failures produce a safe "not enough context" message instead of a crash. If ChromaDB has a dimension mismatch at startup, the collection is auto-deleted and rebuilt (`vectorstore.py`). The front-desk integrations never fail the turn: missing keys become `dry_run` results, request failures are caught and reported as an `error` line in the "Front desk actions" block, and `front_desk.process_accept` has a final safety net so it never raises. At the API level, if `run_graph` throws an unhandled exception, it's caught in `main.py` and returned as an SSE `error` event rather than a 500. On the frontend, `useChat.ts` catches network errors and displays them inline. The core principle is: no user-facing blank screen from an infrastructure failure.

**Code Reference:** `nodes/rag.py`, `services/vectorstore.py`, `services/front_desk.py` (`_run`), `main.py` (`event_stream`)

**Gotcha to Avoid:** Don't claim all errors are handled. Acknowledge that error handling is layered degradation, not exhaustive coverage.

---

**Q: What's your testing strategy?**

**TL;DR:** Integration tests over the full FastAPI + LangGraph stack with the LLM and RAG monkeypatched — 56 tests, all offline.

**Full Answer:** The 45 integration tests in `tests/test_backend_integration.py` (plus 7 contract-scaffold tests) exercise the full stack from HTTP request to SSE response, using FastAPI's `TestClient`. The RAG LLM client is monkeypatched away (`_build_client_or_none` returns `None`, forcing the fallback path) and retrieval is replaced with a fixed dental chunk, so the suite is hermetic and runs offline in ~25 seconds. Routing needs no stubbing at all — it's deterministic, and `test_routing_is_a_pure_function_without_any_llm` asserts that directly. The tests cover all three intake flows end-to-end, the invalid-input matrix for every field type (including `pain_level: -2`, `last_visit_year: 2031`, and `"i like dogs"` as a patient name), the RAG fallback path, mid-flow interruption and exact resumption, accept/adjust/restart, service switching, compact multi-field input for all services, and the front-desk integrations — dry-run, real-payload (with monkeypatched `urllib`), and error paths. There are no frontend tests.

**Code Reference:** `tests/test_backend_integration.py` (fixture at the top), `tests/test_contract_scaffold.py`

**Gotcha to Avoid:** Don't oversell coverage. Acknowledge what's not tested: the LLM client retry logic against a real API, the vectorstore embedding pipeline quality, and all frontend behavior.

---

**Q: How do you validate inputs?**

**TL;DR:** Two independent layers: coerce-and-validate at collection time, then re-validate before estimation.

**Full Answer:** The first layer is in `collect_details.py`'s `_coerce_value` function. As each field answer arrives, it's coerced to the target type (int, email, phone, str), checked against min/max range (`pain_level` 0–10, `last_visit_year` 1901–current year), and matched against an allowed-values list with synonym normalization ("out of pocket" → `self_pay`). If it fails, a human-readable error message is generated and the same field is re-prompted — the pointer doesn't advance. There's also a `_clean_text_value` function for string fields that catches question-shaped answers ("do you offer implants"), dental-domain words used as answers, and a denylist for junk names — `"i like dogs"` as a patient name is rejected. The second layer runs in `validate_visit.py` before the estimator is called — `validate_visit_inputs` re-validates all collected fields as a coherent set. This belt-and-suspenders approach means even if a bug in the first layer lets bad data through, the estimator never receives invalid inputs.

**Code Reference:** `nodes/collect_details.py` (`_coerce_value`, `_clean_text_value`), `services/visit_estimator.py` (`validate_visit_inputs`)

**Gotcha to Avoid:** Don't forget to mention the `ChatRequest` Pydantic model at the API boundary (`main.py`) — that's the first validation layer at the HTTP level.

---

**Q: Show me code you're most proud of and why.**

**TL;DR:** The deterministic router's `decide` function — it's the most carefully engineered piece of the system.

**Full Answer:** I'd point to `decide` in `nodes/router.py`. The problem it solves is real: in a mixed Q&A-plus-workflow bot, the single hardest decision is what a message *is* — a field answer, a question, a booking request, or a confirmation. An LLM classifier frequently gets short inputs like "2024" or "morning" wrong. `decide` encodes the insight that in every reachable state the classification is unambiguous if you order the rules correctly: restart always wins; a `?` while a field is pending is always a question (even if it mentions "appointment"); whole-word booking hints start or switch an intake ("Booker Smith" doesn't trigger, because matching is word-bounded); a pending field absorbs anything else; and a confirm-step reply with a negation token ("no, this is not ok") can never be read as an accept — important because accept is the one action with external side effects. It's compact, pure, thoroughly tested, and it means the same inputs always produce the same route.

**Code Reference:** `nodes/router.py` (`decide`, `interpret_confirmation`)

**Gotcha to Avoid:** Don't just say "I'm proud of all of it." Pick one thing, explain the problem it solves, and explain why the implementation is good.

---

**Q: Show me code you'd refactor if you had time.**

**TL;DR:** The synchronous `urllib.request` LLM client — it blocks threads under concurrency.

**Full Answer:** `services/llm.py`'s `_stream_chat_text` and `_request_json` use `urllib.request.urlopen`, which is blocking. Every concurrent LLM call occupies a thread-pool worker for 1-3 seconds. For the demo volume this is fine, but it's the right thing to replace. I'd switch to `aiohttp` and make the LLM client fully async — `async def chat_text(...)` returning an async generator. That would eliminate the `run_in_executor` bridge in `main.py` and let FastAPI's event loop handle many concurrent streams without thread exhaustion. A second candidate is the cleaning-specific compact-input merger in `collect_details.py` — the generic comma-separated parser now covers all services, but the cleaning flow still has an extra unordered-fragment merger with field-specific branches that could be generalized.

**Code Reference:** `services/llm.py` (`_request_json`, `_stream_chat_text`), `nodes/collect_details.py` (`_merge_cleaning_multi_field_input`)

**Gotcha to Avoid:** Pick the actual remaining issue (sync HTTP), not something already fixed.

---

## AI/LLM-Specific Questions

---

**Q: Why this model and provider?**

**TL;DR:** OpenRouter for flexibility; a small, cheap default model because the LLM's only job here is grounded prose.

**Full Answer:** OpenRouter lets the reviewer use their own API key without being locked to one provider, and lets me swap the model via the `OPENROUTER_MODEL` env var without touching code — the code default is `openai/gpt-4o-mini`, and the Docker deployment config defaults to `meta-llama/llama-3.1-8b-instruct`. For this application, the LLM has exactly one job: write a grounded answer to a dental question from retrieved context. Routing, field collection, validation, estimation, and the front-desk integrations never touch it. Both default models are cheap enough that a full demo session costs fractions of a cent, and because the RAG node has a deterministic fallback (formatted chunk answers), a weaker model degrades quality rather than correctness. If I needed better prose on edge cases, I'd switch to a larger model via the same env var, with no code changes.

**Code Reference:** `services/llm.py` (`DEFAULT_MODEL`), `env.example`, `docker-compose.backend.yml`

**Gotcha to Avoid:** Don't apologize for using a small model. Explain why it's sufficient for the task and what you'd change if quality requirements increased.

---

**Q: How do you handle hallucinations?**

**TL;DR:** The system prompt constrains the LLM to answer only from context, and estimate numbers never come from the LLM.

**Full Answer:** Two mechanisms. First, the RAG system prompt (`rag.py`) establishes the persona — "Ivory, the AI front desk for Ivory Dental Studio — warm, precise, and educational" — and explicitly instructs: answer only using the provided knowledge base context; you provide dental health education, never medical advice or a diagnosis; if the context is insufficient, say so plainly and do not invent clinic or dental details; cite the knowledge-base source. This doesn't eliminate hallucinations entirely, but it significantly reduces the surface area. Second, and more importantly, the highest-stakes output — the visit estimate — is never generated by the LLM. It's calculated by a deterministic fee schedule in `services/visit_estimator.py`, and every estimate carries the disclaimer "Educational estimate — not a diagnosis or a final price." The LLM cannot hallucinate a price or a diagnosis. The worst case is in the knowledge Q&A flow, where the fallback message ("I do not have enough knowledge-base context to answer that confidently right now.") is the safe default.

**Code Reference:** `nodes/rag.py` (`RAG_SYSTEM_PROMPT`), `services/visit_estimator.py` (`ESTIMATE_DISCLAIMER`)

**Gotcha to Avoid:** Don't claim hallucinations are "solved." The LLM can still fabricate details in the RAG path. Acknowledge the mitigations and their limits.

---

**Q: What's your prompt engineering approach?**

**TL;DR:** One focused prompt — the RAG answer prompt — with tight constraints; everything else is deterministic code.

**Full Answer:** There is exactly one place where a prompt is used: the RAG node. The system prompt (`rag.py`) establishes persona ("Ivory, the AI front desk for Ivory Dental Studio"), scope constraints ("answer only using the provided knowledge base context", "never medical advice or a diagnosis"), behavioral guidance ("suggest booking a visit when it is relevant", "cite the knowledge-base source"), and an intake-safety rule ("do not reset intake progress"). The user prompt is the question plus the numbered retrieved chunks, and up to six recent conversation turns are passed as history so follow-up questions resolve in context. I deliberately kept it short — long prompts increase token costs and give a small model more ways to go off-script. The most important prompt engineering decision was structural, not textual: removing the LLM from classification entirely. There is no intent-classification prompt because the router is a deterministic function.

**Code Reference:** `nodes/rag.py` (`RAG_SYSTEM_PROMPT`, `_build_prompt`, `_recent_history`)

**Gotcha to Avoid:** Don't say you "optimized" the prompt without specifics. Explain what problem each constraint solves.

---

**Q: How do you control cost and token usage?**

**TL;DR:** Cheap model, one short prompt, strict `max_tokens`, and a deterministic core that skips the LLM entirely.

**Full Answer:** Four mechanisms. First, the default model is small and cheap (`openai/gpt-4o-mini` by default, swappable via env var). Second, the RAG response is capped at `max_tokens=450` with `temperature=0.2` (`rag.py`). Third, history sent to the LLM is bounded to the most recent six turns, not the whole transcript. Fourth — and most impactful — the LLM is only called on the RAG path. Every intake turn (field prompts, validation errors, estimates, confirmations, the front-desk block) is deterministic Python with zero LLM calls. A complete intake from "book a cleaning" to "accept" costs nothing in tokens. If costs were a concern at scale, I'd add an LRU cache on common RAG queries — questions like "what does a routine cleaning include?" are asked repeatedly and have stable answers.

**Code Reference:** `nodes/rag.py` (`max_tokens=450`, `_recent_history`), `nodes/router.py` (no LLM)

**Gotcha to Avoid:** Don't make up numbers. Use the actual `max_tokens` values from the code.

---

**Q: How would you evaluate output quality?**

**TL;DR:** I don't have a formal eval pipeline — this is an honest gap. Here's what I'd build.

**Full Answer:** Currently there's no automated quality evaluation beyond the integration tests (which check for specific strings, not quality). For a production system, I'd build two evaluation tracks. For RAG answers: a small labeled dataset of (question, expected_answer) pairs — sourced from the NIDCR/CDC-grounded knowledge base — with a judge LLM scoring groundedness (is the answer supported by the retrieved context?) and relevance (does it answer the question?). Medical-adjacent content raises the bar: I'd specifically test that answers never drift into diagnosis or treatment advice. For the intake flow, the deterministic router and estimator are easy to evaluate: the routing table test asserts exact routes for a matrix of (state, message) pairs, and the estimator has known inputs and expected outputs. The hardest thing to evaluate is the mode-switching behavior — whether the bot correctly stays in intake mode versus drifting to conversational mode — which is why the integration tests cover that path exhaustively.

**Code Reference:** `tests/test_backend_integration.py` (`test_routing_is_a_pure_function_without_any_llm`, mid-flow tests)

**Gotcha to Avoid:** Don't pretend you have an eval pipeline if you don't. Interviewers respect "this is what I'd build" over a fabricated answer.

---

**Q: What happens when the OpenRouter API is down or slow?**

**TL;DR:** The bot stays operational — the intake flow never uses the LLM, and RAG falls back to formatted chunk answers.

**Full Answer:** The LLM client (`services/llm.py`) has a retry loop with exponential backoff (up to 2 retries by default, delay capped at 4 seconds). If all retries fail, it raises `OpenRouterError`. In the RAG node (`rag.py`), an LLM failure falls back to `_format_fallback_answer`, which generates a direct text answer from the retrieved chunks without the LLM — including curated direct answers for common questions like toothache first steps and "what services do you offer". The `/debug` endpoint shows LLM reachability status, so a developer can quickly diagnose connectivity issues. During a demo, if OpenRouter is slow, RAG responses will be delayed but correct; if it's completely down, Q&A degrades gracefully and the intake flows continue working perfectly since routing, validation, and estimation never touch the LLM.

**Code Reference:** `services/llm.py` (`_request_json` retry loop), `nodes/rag.py` (`_format_fallback_answer`), `main.py` (`/debug`)

**Gotcha to Avoid:** Demonstrate you've actually tested this scenario — the integration tests monkeypatch the LLM away, which is effectively testing the "LLM unavailable" path.

---

## Trade-offs & Decision Making

---

**Q: How does the real SSE streaming work?**

**TL;DR:** OpenRouter streams tokens → thread-local callback → asyncio queue → SSE generator.

**Full Answer:** The LLM call runs in a thread-pool executor (via `run_in_executor`) because LangGraph is synchronous. To bridge that thread to the async FastAPI SSE generator, I use a thread-local `on_token` callback (`streaming_context.py`). Before calling `run_graph`, the SSE handler registers a callback in thread-local storage. Deep inside the LangGraph execution, `rag.py` calls `get_on_token()` and passes it to `llm.chat_text()`. The LLM client (`services/llm.py` `_stream_chat_text`) uses OpenRouter's `"stream": True` API, parses the `data:` SSE lines, and calls `on_token(delta)` on each token. That callback does `loop.call_soon_threadsafe(queue.put_nowait, token)`, putting the token into the asyncio queue. The SSE generator on the main thread drains the queue with `await queue.get()` and yields `token` events to the browser. A sentinel `None` signals completion. If no tokens were emitted (deterministic replies like field prompts, validation errors, and estimates never call the LLM), the handler falls back to word-level simulation of the final message so the UX stays consistent.

**Code Reference:** `streaming_context.py`, `main.py` (`event_stream`, `_run_in_thread`), `services/llm.py` (`_stream_chat_text`), `nodes/rag.py` (`get_on_token` usage)

**Gotcha to Avoid:** Don't say streaming is simulated — it's real token streaming from OpenRouter on the RAG path. The word-simulation fallback only fires when the graph never calls the LLM (e.g., an intake field prompt).

---

**Q: What was the hardest technical decision?**

**TL;DR:** Deciding where to put the state — frontend or backend — and committing fully to backend-controlled state.

**Full Answer:** The hardest architectural decision was making the backend the single source of truth for all state, including the current field, mode, and intake progress. The alternative — storing state in React and sending it with each request — would have simplified the backend but created a split-brain problem: what if the frontend's state diverges from what the backend expects? By having the backend own state completely (in the LangGraph checkpointer), the frontend becomes a pure render layer. It receives a `session` snapshot with every SSE `message_complete` event and updates its UI to match — the flow chip, the progress bar, and the visit-confirmation gate are all driven by `mode`, `intake_step`, and `has_visit_estimate` from the backend. The cost is that the frontend can't optimistically update — it must wait for the backend to confirm a state transition. For a chatbot, this is the right trade-off; the alternative would have caused subtle bugs where the user's UI shows "Collecting details" but the backend thinks we're in "confirm."

**Code Reference:** `main.py` (`_public_session_state`), `frontend/src/hooks/useChat.ts`

**Gotcha to Avoid:** Don't say "all decisions were easy." This is a real architectural tension that has concrete implications.

---

**Q: Where did you cut corners and why?**

**TL;DR:** I originally cut five corners to ship fast — and then fixed them before the final demo.

**Full Answer:** The original version had five deliberate scope cuts: a hand-rolled in-memory session store, simulated word-level SSE streaming, a `NEXT_PUBLIC_` password exposed in the client bundle, open CORS (`allow_origins=["*"]`), and no rate limiting. I made each tradeoff explicitly to move fast on the core behavior — state machine, RAG, deterministic estimator. Once the core was solid, I fixed them: conversation state now lives in the LangGraph checkpointer (one source of truth, no manual save); streaming is real OpenRouter tokens via thread-local callback into an asyncio queue; auth is an HMAC-SHA256 httpOnly cookie with credentials in server-side env vars only, enforced on the `/api/chat` and `/api/reset` proxies; CORS is restricted to `ALLOWED_ORIGINS`; `slowapi` rate limits `/chat` at 60/min and `/reset` at 20/min. The genuine remaining tradeoffs are the in-memory checkpointer (sessions lost on restart) and the synchronous `urllib.request` LLM client — both are production-hardening items, not demo blockers.

**Code Reference:** `graph.py` (checkpointer), `main.py` (CORS, rate limiter), `streaming_context.py`, `frontend/app/api/auth/`

**Gotcha to Avoid:** Don't present the original five gaps as still open. Explain both why they were originally cut AND that they were fixed, so you demonstrate the full decision arc.

---

**Q: What's the biggest risk in this architecture?**

**TL;DR:** The in-memory checkpointer and the synchronous LLM client under concurrency; plus a stateless session token model.

**Full Answer:** The open-CORS and no-rate-limit risks are fixed — CORS is locked to `ALLOWED_ORIGINS` and `slowapi` limits are in place. The remaining risks are: (1) The checkpointer is `MemorySaver` — all conversation state is lost on a backend restart, and horizontal scaling would split sessions across workers. The fix is a persistent LangGraph checkpointer (Redis/Postgres). (2) The LLM client uses `urllib.request` (synchronous), so under high concurrency each `/chat` request that hits the LLM blocks a thread for 1-3 seconds. Under heavy load this exhausts the thread pool before the rate limiter can help. (3) The session token is stateless — HMAC-SHA256 of `AUTH_USERNAME:AUTH_PASSWORD` — so there's no way to invalidate individual sessions; changing the password invalidates all sessions at once. For a demo this is fine; for a multi-user production app you'd want a token store with per-session revocation. (4) The backend has no authentication of its own — the httpOnly cookie protects the Next.js proxies, but the FastAPI API is still open on `localhost:8000`.

**Code Reference:** `graph.py` (`MemorySaver`), `services/llm.py`, `frontend/app/api/auth/_auth.ts` (`hmacToken`)

**Gotcha to Avoid:** Don't cite already-fixed items as risks. Lead with what actually remains.

---

**Q: If you had 2 more weeks, what would you add?**

**TL;DR:** The production-readiness fixes are done — the next two weeks would be persistence, async, and observability work.

**Full Answer:** Week 1: A persistent LangGraph checkpointer (Redis or Postgres) so sessions survive restarts and multiple workers can share state. Then async LLM HTTP — replace `urllib.request` with `aiohttp` so the FastAPI event loop handles concurrent LLM requests without thread-pool exhaustion. Real Cal.com availability lookup — today the booking start time is computed deterministically (next business day at 09:00/13:00/17:00 UTC for morning/afternoon/evening); a real front desk would query open slots first. Week 2: Observability — a Prometheus `/metrics` endpoint tracking LLM latency histogram, error rate by endpoint, and intake completion rate by service. Export the `trace_id` (already generated per turn in `graph.py`) to OpenTelemetry. Add frontend tests — currently there are none. The visit card already exports JSON/CSV; a patient-friendly PDF/email summary would round that out.

**Code Reference:** `graph.py` (checkpointer, `trace_id`), `services/calcom.py` (`next_business_day_start`), `frontend/src/components/VisitCard.tsx` (export logic)

**Gotcha to Avoid:** Don't list already-shipped items as future work (e.g. conversation history in the RAG context is already implemented via `_recent_history`).

---

## Production & Operations

---

**Q: How would you deploy this?**

**TL;DR:** Backend as a Docker container via docker-compose or Kubernetes; frontend deployed to Vercel or as a Docker container.

**Full Answer:** The backend has a production-ready `Dockerfile` already. It uses `python:3.12-slim`, installs dependencies, copies source, and runs `uvicorn main:app --host 0.0.0.0 --port ${PORT} --proxy-headers`. The `docker-compose.backend.yml` shows the full deployment config: persistent volume for ChromaDB and model weights at `/data`, environment variables for secrets (including the optional, commented-out front-desk integration keys), and a healthcheck that hits `/health`. For the frontend, `next build` + `next start` runs on Node.js — it deploys to Vercel with zero config, or as a Docker container for self-hosted. `BACKEND_API_BASE_URL` environment variable connects the Next.js proxy to wherever the FastAPI backend is running. The backend image is published as `kpg782/ivory-backend:latest`.

**Code Reference:** `backend/Dockerfile`, `docker-compose.backend.yml`, `frontend/app/api/chat/route.ts`

**Gotcha to Avoid:** Don't just say "deploy to the cloud." Know the specifics: which ports, which env vars, what the healthcheck does.

---

**Q: How would you monitor this in production?**

**TL;DR:** Currently: structured Python logging + `/health` + `/debug` endpoints. What I'd add: Prometheus metrics + distributed tracing.

**Full Answer:** Right now: `logging.basicConfig(level=logging.DEBUG)` in `main.py` gives structured logs for every request, LLM call, retrieval result, and integration attempt. The `/health` endpoint returns `{"status": "ok"}` for uptime monitoring. The `/debug` endpoint shows KB status with a retrieval probe ("what dental services do you offer"), LLM reachability, session count, session backend (`langgraph-checkpointer`), CORS origins, and whether rate limiting is enabled — useful for diagnosing issues without SSH access. What I'd add in production: a Prometheus `/metrics` endpoint tracking LLM latency histogram, error rate by endpoint, intake completion rate by service type, integration success/dry-run/error counts, and active session count. I'd also export the per-turn `trace_id` to OpenTelemetry so I can trace a request from the browser through Next.js into FastAPI and into the LLM call.

**Code Reference:** `main.py` (logging setup, `/debug`), `graph.py` (`trace_id`)

**Gotcha to Avoid:** Don't say "I'd add Datadog" without explaining what you'd instrument. Be specific about the metrics that matter for this application.

---

**Q: How do you handle secrets and env vars?**

**TL;DR:** Backend secrets in `.env`/shell; frontend credentials in server-side env vars only — nothing sensitive in the client bundle.

**Full Answer:** The backend's `env.py` loads `.env` files from the backend directory and repo root using `python-dotenv` with `override=False` — shell env vars take precedence. In Docker, secrets are injected via `environment:` in `docker-compose.backend.yml`. The only required secret is `OPENROUTER_API_KEY`; the front-desk integration keys (`AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`, `CALCOM_API_KEY`, `CALCOM_EVENT_TYPE_ID`, `RESEND_API_KEY`) are optional — when absent, the integrations run in dry-run mode and never touch the network. On the frontend, `BACKEND_API_BASE_URL` is server-side (no `NEXT_PUBLIC_` prefix), so the backend URL never reaches the browser. Auth credentials (`AUTH_USERNAME`, `AUTH_PASSWORD`) and `SESSION_SECRET` are also server-side env vars in `frontend/.env.local` — they're read by the Next.js API routes (`app/api/auth/`) and never bundled into client JavaScript. The only `NEXT_PUBLIC_` auth vars are `NEXT_PUBLIC_AUTH_DEMO_USER`, an optional username hint for the login screen, and `NEXT_PUBLIC_AUTH_DEMO_LOGIN`, the one-click demo-login flag. The password is intentionally not exposed. Previously the password was in `NEXT_PUBLIC_IVORY_LOGIN_PASS` — that's been removed entirely.

**Code Reference:** `backend/env.py`, `frontend/app/api/auth/_auth.ts`, `frontend/.env.example`, `env.example`

**Gotcha to Avoid:** Don't mention `NEXT_PUBLIC_IVORY_LOGIN_PASS` as a current issue — it's been removed. Explain how auth was fixed (server-side env vars + httpOnly cookie).

---

**Q: What's your CI/CD strategy?**

**TL;DR:** Currently none. Here's what I'd set up.

**Full Answer:** The project doesn't have CI/CD configured yet — it was built as an assessment. For a production setup: a GitHub Actions workflow that runs `pytest tests/` on every PR (the 56 tests run without any external dependencies since the LLM, retrieval, and integrations are monkeypatched or dry-run). A `typecheck` step running `tsc --noEmit` for the frontend. On merge to main: build and push the Docker image to Docker Hub (already using `kpg782/ivory-backend`), and trigger a Watchtower pull on the production host (or update the ECS task definition, or ArgoCD sync, depending on the platform). The backend healthcheck in `docker-compose.backend.yml` handles zero-downtime via the `start_period: 45s` grace period for model loading.

**Code Reference:** `pytest.ini`, `frontend/package.json`, `docker-compose.backend.yml`

**Gotcha to Avoid:** Don't claim you have CI/CD if you don't. "Here's what I'd build" is a better answer than a fabricated pipeline.

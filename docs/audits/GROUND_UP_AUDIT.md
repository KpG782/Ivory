# Ivory — Ground-Up Architecture Audit

**Date:** 2026-06-09
**Scope:** End-to-end — LangGraph orchestration, state/persistence, intent routing, RAG, the quote flow, the cross-mode "context switching," and the Next.js frontend.
**Method:** Full read of `backend/` and `frontend/` against the documented design (`README.md`, `LAYMAN_MENTAL_MODEL_FLOW.md`).

**Severity legend:** 🔴 Critical (breaks a core promise) · 🟠 High · 🟡 Medium · ⚪ Low/polish.

---

## Executive summary

Ivory is supposed to be **one conversation** that fluidly switches between answering insurance questions (RAG) and running a step-by-step quote, and can **resume a quote exactly where it left off** after an interruption.

The audit's core finding: **that behavior is simulated, not real.** Four structural decisions, each individually reasonable, combine to make the promise fragile:

1. 🔴 **The graph is stateless and state is hand-rolled.** The `StateGraph` is compiled with no checkpointer (`graph.py:157,160`); persistence is a custom `_SessionStore` (`main.py:83-144`) that the request handler manually loads from and writes to. The write isn't transactional, so an error mid-turn silently drops the turn.
2. 🔴 **"Resume after interruption" is a string trick.** When a user asks a question mid-quote, the system answers and **glues** `"Now, back to your auto quote — what is the vehicle make?"` onto the end of the answer (`graph.py:52-61`). It only works because the field name happens to survive in the manually-persisted state. There is no real pause/resume.
3. 🔴 **RAG has no conversation memory.** The prompt sent to the LLM is only the *current* question + retrieved chunks (`rag.py:189-206`). A follow-up like "what's the maximum benefit?" after "tell me about life insurance" cannot work — which is the literal opposite of "one conversation."
4. 🟠 **Routing guesses intent from punctuation and keywords.** A 3-tier heuristic stack (`router.py`) decides field-answer vs. question vs. quote by looking for `?` and word lists. Compound inputs ("I'm 30, but what's comprehensive coverage?") and ambiguous words ("home" is both a product and a valid location answer) misroute. Worse, the computed `intent` is then partly **ignored** by the router.

Everything below is the evidence. The remediation (a LangGraph-native rebuild) is summarized at the end and specified in `plans/great-for-now-i-abstract-seal.md`.

---

## 1. Orchestration & state

### 1.1 🔴 No checkpointer — persistence is reinvented by hand
- The graph is compiled bare: `return graph.compile()` (`graph.py:157`), `COMPILED_GRAPH = _build_graph()` (`graph.py:160`). No `checkpointer=`, no `thread_id`.
- Each turn manually does: load state from `_SessionStore` (`main.py:267`), append the user message and `invoke` (`graph.py:163-172`), then write the whole state back (`main.py:309`).
- `_SessionStore` (`main.py:83-144`) re-implements per-session storage (in-memory dict + optional Redis with JSON (de)serialization) — exactly what LangGraph's checkpointer provides natively, including the `messages` reducer, atomic per-thread snapshots, and resumability.

**Impact:** Three sources of truth for "session state" (the dict, Redis, and whatever the graph returns) that must be kept in sync by hand; no native resume; brittle JSON round-tripping of the whole `ChatState` every turn.

### 1.2 🔴 State write is not transactional
- The save `SESSION_STORE[payload.session_id] = next_state` (`main.py:309`) runs **after** the graph finishes and is **not** in a `try/finally`.
- If any node raises, the handler hits the error branch (`main.py:305-307`) and returns **without saving** — the turn is lost and the session silently reverts to its previous snapshot. The user saw a partial response get generated but the state never advanced.

### 1.3 🟠 `intent`, `mode`, and `quote_step` are overlapping sources of truth
- `route_after_router` (`router.py:106-122`) routes on `intent` for `"question"`/`"quote"`, but for everything else **falls through to `quote_step`**. The classifier's `"response"` result is never used for routing — it's dead.
- So routing is really driven by `quote_step`, while `intent`/`mode` are computed alongside it and can disagree. This is the kind of hidden coupling that makes "why did it go there?" hard to answer.

### 1.4 🟡 Clone-everywhere with unclear ownership
- Every node wraps its work in `clone_state(...)` (deep copy of the whole dict) and re-wraps the result in `ChatState(**...)` (`graph.py:16-84`). Some nodes (e.g. `confirm`) then mutate in place. The mutation/ownership model is inconsistent and pays a deep-copy cost per node per turn.

---

## 2. Intent routing (the heuristic tower)

### 2.1 🟠 Three overlapping classifiers keyed on punctuation/keywords
- `classify_intent` (`router.py:39-55`) chains: `_classify_deterministic` (`58-103`) → `_classify_with_rules` (`184-224`) → `_classify_with_llm` (`136-167`).
- The deterministic/rules layers decide field-answer vs. question largely by: presence of `?`, and membership in hand-maintained sets `QUESTION_HINTS`, `QUOTE_HINTS`, `PROGRESSION_HINTS`, etc. (`router.py:9-36`).

**Failure modes (confirmed by reading the branches):**
- 🟠 **Compound inputs.** "I'm 30, but what's comprehensive coverage?" contains both a field answer *and* a question. The negative heuristic "no `?` ⇒ it's a field answer" (`router.py:92`) and its inverse can't represent "answer the field, then take the question."
- 🟠 **Ambiguous tokens.** "home" is in `_PRODUCT_KEYWORDS` (`router.py:170-181`) **and** a plausible answer to "which city?". `detect_product` (`identify_product.py:34-41`) substring-matches it anywhere in the message.
- 🟡 **Small-model misclassification** is the very thing the deterministic guards exist to paper over (see the comments at `router.py:45-50, 76-78`) — a sign the classification problem is being solved at the wrong layer.

### 2.2 🟡 LLM classifier is unguarded JSON
- `_classify_with_llm` (`router.py:136-167`) asks for `{"intent": ...}` with no schema validation beyond "is it one of three strings," and silently swallows all exceptions to `None`.

---

## 3. RAG (retrieval-augmented generation)

### 3.1 🔴 No conversation history in the prompt
- `_build_prompt` (`rag.py:189-206`) constructs `Question / Knowledge-base context / Instructions` from only the **current** query + retrieved chunks. Prior turns are never sent to the LLM.
- The `messages` list is used *only* to extract a single query string (`_extract_query`, `rag.py:153-168`).
- **Note for the fix:** `OpenRouterClient.chat()` (`llm.py:110-139`) already accepts a full `messages` array — the capability exists; RAG just doesn't use it. Adding history is low-risk.

### 3.2 🟠 Naive single-shot retrieval, no history-aware query
- The raw latest message is embedded and searched as-is (`vectorstore.search_knowledge_base`). A follow-up ("what's the deductible?") is retrieved with no knowledge of the product established two turns earlier. No query condensation/rewrite.

### 3.3 🟡 No relevance floor; chunks have no overlap
- Retrieval re-ranks then returns top-k with **no minimum-similarity threshold**, so a weak match is still injected into the prompt.
- Ingestion splits on paragraph boundaries with **no overlap** (`vectorstore._chunk_document`), so a fact straddling a boundary can become unretrievable.

### 3.4 🟡 Silent fallback to hash embeddings
- If `sentence-transformers` can't load, the vector store silently switches to hash-based pseudo-embeddings. Retrieval quality collapses with **no signal** in logs or `/debug`.

---

## 4. Quote flow & context-switching — the root cause

The deterministic quote machinery is **good** and worth keeping: per-product `FIELD_SPECS` (`collect_details.py:18-100`), `_coerce_value` validation (`292-347`), `validate_quote_inputs` + `calculate_quote` (`quote_calculator.py`). The problem is entirely in *how turns are orchestrated around it*.

### 4.1 🔴 "Interrupt and resume" is faked
- Mid-quote question handling: the router stashes `pending_question` (`graph.py:35-36`); RAG answers; then `_rag_node` **appends a sentence** re-asking the pending field (`graph.py:46-61`). `pending_question` itself is only ever used as a fallback query string (`rag.py:153-168`) — it is not a resume mechanism.
- There is no real "pause here, come back to this exact point." It survives only because `current_field` persists in the hand-rolled state and the next turn re-enters the global router.

### 4.2 🟠 The fragile decision is made in the wrong place
- "Is this message the field answer, or a question?" is decided at the **global router**, which has only weak signals. The router doesn't lean on the strongest signal available: *does this input actually validate as the field we're waiting for?* That check lives later, in `collect_details`/`_coerce_value`, after routing has already been committed.

### 4.3 🟡 Product-switch is destructive with no resume
- Switching products mid-quote calls `_reset_quote_progress` (`graph.py:26-33,175-182`), nuking all collected data with no way to return to the original quote.

### 4.4 ⚪ Input-coercion sharp edges
- `LOCATION_DENYLIST` (`collect_details.py:8-15`) can reject legitimate single-token place names; the multi-field auto regex (`collect_details.py:159-222`) is a brittle chain of substitutions sensitive to phrasing.

---

## 5. Frontend (Next.js) — UI/UX

**Foundation is genuinely good** and should be preserved: working SSE token streaming (`lib/sse.ts`, `hooks/useChat.ts`), HMAC-cookie auth (`app/api/auth/*`), localStorage session history, a deliberate visual language (Manrope + Space Grotesk, ink/sand/gold/cyan tokens, Tailwind v4 `@theme`, custom animations, `prefers-reduced-motion` respected). **Recommendation: polish, do not redesign.**

Real issues:
- 🟠 **Oversized units.** `App.tsx` (~592 lines) mixes login, sidebar, header, and chat; `hooks/useChat.ts` (~690 lines) mixes auth, session, streaming. Hard to test and reason about. → split.
- 🟠 **No markdown rendering.** Assistant answers render as plain text; any markdown the LLM emits shows as literal characters. → `react-markdown`.
- 🟠 **Re-render churn while streaming.** The message list re-creates on every token; all bubbles re-render. → `React.memo` on `MessageBubble`.
- 🟠 **No error boundary.** A render error blanks the whole app.
- 🟡 **Fuzzy quote-result detection** (`useChat.ts:144-172`) sniffs keys (`"premium" in value || ...`) instead of trusting an explicit field.
- 🟡 **Export-status text flashes** with no auto-clear timeout (`components/QuoteCard.tsx`).
- 🟡 **Accessibility gaps:** some buttons lack a visible focus ring; cyan indicator and `slate-500` body text are borderline on contrast; state/streaming pills aren't announced (`role="status"`).
- ⚪ Login input doesn't auto-focus; no "clear history"; no connection/health indicator; localStorage quota unchecked.

---

## 6. Cross-cutting hardening
- 🟡 `ChatRequest.message` has a min length but **no max** (`main.py:149-151`) — unbounded input.
- 🟡 `/debug` leaks model id prefix and session backend; fine for a demo, revisit before public exposure.
- ⚪ Rate limiting (`slowapi`) and CORS allow-list are present and reasonable.

---

## 7. Prioritized remediation (→ the rebuild)

| # | Finding | Severity | Fix direction |
|---|---------|----------|---------------|
| 1 | No checkpointer; hand-rolled, non-transactional state | 🔴 | LangGraph checkpointer + `thread_id=session_id`; delete `_SessionStore`; `messages` reducer |
| 2 | Faked interrupt/resume (string append) | 🔴 | Real `interrupt()`/`Command(resume=...)` in the quote flow |
| 3 | RAG has no memory | 🔴 | Pass recent history to `chat()`; history-aware query condense |
| 4 | Heuristic intent in the wrong layer | 🟠 | Slim structured-output classifier at conversation start; in-context resume classification (validate-as-field first) inside the quote flow |
| 5 | Destructive product-switch, no relevance floor, no overlap, silent embed fallback | 🟡 | Add resume affordance; similarity floor; chunk overlap; log fallback |
| 6 | Frontend: oversized files, no markdown/memo/error-boundary, a11y gaps | 🟠–🟡 | Split components/hooks; add capabilities; a11y polish (keep design language) |
| 7 | Unbounded message input | 🟡 | `max_length` on `ChatRequest` |

The single conceptual shift: **stop simulating a stateful, resumable conversation and let LangGraph *be* one** — checkpointer for memory, `interrupt()` for the bookmark, history-aware RAG for continuity, and move the fragile "answer vs. question" call to where it has the most context.

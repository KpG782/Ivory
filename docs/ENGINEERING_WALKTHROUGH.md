# ShieldBase — How the LangGraph / LangChain Setup Was Built & Orchestrated

**Audience:** a software / AI engineer who wants to understand *how this was put together*, step by step — but every step is also explained 🧸 **like you're five** so you can re-explain it in your own words.

> **First, clear up one word: "training."**
> Nothing here is *trained*. There is no model fitting, no fine-tuning, no gradient descent, no dataset of labels. We use **two pre-built brains off the shelf** — a sentence-embedding model (to turn text into numbers for search) and a hosted chat model (to write answer sentences) — and we **orchestrate** them with rules. "Building this" means **wiring**, not **training**. Whenever someone says "how did you train it," the honest answer is: *"I didn't train anything — I orchestrated retrieval + rules + a hosted model."* That distinction is the whole point of this document.

---

## 0. The one rule that explains everything

🧸 **The robot is allowed to *write*, never to *drive*.** A fixed rule-card decides what happens next. The AI only fills in the words of an answer.

🛠 **Control flow is deterministic; generation is the only probabilistic part.** Every state transition is a pure function `decide(state, message) → route`. The LLM is called in exactly one place (`nodes/rag.py`) and only to produce *answer text*. It can never change which state we're in. This makes the system **testable** (same input → same route) and **defensible** (you can point at the exact rule that fired).

Everything below is a consequence of this one rule.

---

## 1. The mental model

🧸 Picture a front-desk helper, **Sara**, with three things:
- 📖 a **handbook** to answer questions,
- 📋 a **clipboard form** to get you a price (boxes filled one at a time),
- 📓 an **auto-saving notebook** so she never loses her place.

🛠 The real components:

| Sara | Real component | File |
| --- | --- | --- |
| 📓 auto-saving notebook | LangGraph **checkpointer** (`MemorySaver`), keyed by `thread_id = session_id` | `graph.py` |
| 🃏 rule-card | deterministic `decide(state, message)` | `nodes/router.py` |
| 📋 clipboard form | field specs + per-field validation | `nodes/collect_details.py` |
| 🧮 the pricing math | deterministic actuarial calculator | `services/quote_calculator.py` |
| 📖 handbook | **RAG** = vector search + grounded generation | `nodes/rag.py`, `services/vectorstore.py` |
| ✍️ the writing hand | hosted chat model via a tiny HTTP client | `services/llm.py` |
| 🪟 the service window | FastAPI + Server-Sent Events streaming | `main.py` |

---

## 2. The stack, and what each piece is *for*

🧸 Different tools for different jobs — like a kitchen has a knife, a pan, and an oven.

🛠
- **LangGraph** — the orchestrator. Defines a `StateGraph` of nodes + edges and, crucially, gives us a **checkpointer** so conversation state is persisted per `thread_id` automatically. We do *not* use the LangChain agent/LLM abstractions — only the graph + checkpoint primitives. (That's the "LangGraph, not heavy-LangChain" choice: less magic, more control.)
- **ChromaDB** — the vector database. Stores knowledge-base chunks as embeddings and does nearest-neighbour search.
- **sentence-transformers** — the **embedding** model. Turns a sentence into a ~384-dim vector so "comprehensive coverage" and "non-collision damage" land near each other. *(Pre-trained. We just call it.)*
- **OpenRouter** (custom stdlib client) — the **generation** model. Given system + history + retrieved context, it writes the answer. *(Hosted. We just call it.)*
- **FastAPI + SSE** — the web layer. One POST endpoint that streams tokens to the browser as they arrive.

---

## 3. The build, step by step

Each step is 🧸 then 🛠. This is the order it was actually assembled, leaf-first.

### Step 1 — Decide what we need to remember (the state shape)

🧸 Before Sara can help, decide what goes in her notebook: who you are, what you're buying, which box she's on, what you've answered.

🛠 `state.py` defines `ChatState` (a `TypedDict`). The fields that *drive control flow*:
- `mode` — `"conversational"` or `"transactional"` (just chatting vs. mid-quote)
- `quote_step` — `identify → collect → validate → confirm`
- `insurance_type` — `auto | home | life`
- `current_field` — the exact form box we're waiting on (e.g. `vehicle_make`)
- `collected_data` — answers gathered so far
- `messages` — the running transcript (`{role, content}` dicts; the frontend already speaks this shape)
- `route` — the transient decision for *this* turn (written by the router, read by the edge)

> Design note: state is a **plain dict**, not LangChain message objects. Simpler to serialize, simpler for the frontend, no hidden coupling.

### Step 2 — Turn on durable memory (the checkpointer)

🧸 Give Sara a notebook that **saves itself** every turn — so a stumble (an error) or closing time (a restart) can't erase your page.

🛠 `graph.py` compiles the graph **with a checkpointer**:

```python
_checkpointer = MemorySaver()
COMPILED_GRAPH = _build_graph().compile(checkpointer=_checkpointer)
```

State is now keyed by `thread_id = session_id`. This **replaces** the old hand-rolled session store (load → append → save by hand, saved *after* the work, so a crash mid-turn dropped the turn). Now LangGraph writes the checkpoint atomically as part of each `invoke`.

`MemorySaver` is in-process (great for dev/tests). Because the checkpointer is the *single source of truth*, swapping to cross-restart persistence is a **one-line change** — `SqliteSaver(path)` or a Redis/Postgres saver — with zero changes to nodes or routing.

**Proof it's the source of truth** (`tests/test_backend_integration.py::test_state_persists_across_graph_rebuild`): we throw away the compiled graph object, rebuild it on the *same* checkpointer, and the half-finished quote is still there.

### Step 3 — Build the rule-card (deterministic router)

🧸 One card Sara reads top-to-bottom. The first matching line wins. No guessing, no phoning a robot to decide.

🛠 `nodes/router.py::decide(state, message)` — a **pure function**, no I/O, no LLM:

```python
def decide(state, message):
    text = message.strip().lower()
    # P1 restart while in a quote always wins
    if mode == "transactional" and contains(text, RESTART_HINTS): return "confirm"
    # P2 explicit "...quote..." starts/switches a quote from any state
    if "quote" in text: return "start_quote"
    # P3 waiting for a field: a literal "?" = paused question; else it's the answer
    if current_field:
        return "answer_then_resume" if "?" in text else "collect"
    # P4 quote built, awaiting accept/adjust/restart
    if mode == "transactional" and step == "confirm": return "confirm"
    # P5 choosing a product
    if mode == "transactional" and step == "identify":
        return "identify" if detect_product(text) or affirm(text) else "rag"
    # P6 idle: only explicit buying intent starts a quote; else answer the question
    if "?" not in text and contains(text, QUOTE_INTENT_HINTS): return "start_quote"
    return "rag"
```

Read the priority order out loud and you have the entire conversation policy. Key subtlety: **P3** is the README's "Main Backend Invariant." Mid-field, a literal `?` is the only signal to pause for a question; anything else is handed to the collector, which itself tries to **validate-and-store first** and only re-prompts on failure. (Proof: `test_routing_is_a_pure_function_without_any_llm`.)

### Step 4 — Build the handlers (the nodes that do the work)

🧸 Each station does one job: pick the product, fill a box, do the math, confirm, or answer a question.

🛠 Five handler nodes, each a small function `(state[, message]) → state`:
- `identify_product` — detect `auto/home/life`; if unknown, ask which.
- `collect_details` — the heart of the form. For `current_field`: coerce + validate the input. **Valid → store it and advance** to the next missing field. **Invalid → re-prompt the same field with a specific error.** Reuses `FIELD_SPECS` + `_coerce_value` (kept from the original — they were good).
- `validate_quote` — final cross-field validation, then `calculate_quote(...)` (pure deterministic math in `services/quote_calculator.py`).
- `confirm` — interpret `accept / adjust / restart` deterministically.
- `rag_answer` — the only AI call (Step 7).

Every state therefore has **exactly one defined response and one guardrail**. There is no "the model wandered off" path.

### Step 5 — Wire the graph (nodes + edges)

🧸 Connect the stations with arrows. The rule-card decides which arrow we take out of the front desk.

🛠 `graph.py::_build_graph()`:

```
            START
              │
          ┌───────┐        decide() → route
          │ router│────────────────────────────┐
          └───────┘                             │ (conditional edges)
    ┌──────────┬───────────────┬────────────────┤
    ▼          ▼               ▼                ▼
rag_answer  identify_product  collect_details  confirm
    │          │               │                │
   END   collect_details   validate_quote   collect_details
                                │
                               END
```

- `START → router` always.
- `router → {rag_answer | identify_product | collect_details | confirm}` via `_route_from_router`, which just maps the `route` label the router computed. **The router never routes straight to `validate_quote`** — validation is only reached *after* the last field is collected.
- Downstream conditional edges (`identify→collect`, `collect→validate`, `confirm→collect`) fire only when a node sets the next `quote_step`. Otherwise the turn ends.

One user message = one pass `START → … → END`. The graph does **not** pause mid-run (no `interrupt()`); it processes one turn and ends. The checkpointer carries state to the next turn. This is simpler and *more obviously deterministic* than human-in-the-loop interrupts.

### Step 6 — One turn = one invocation (the loop)

🧸 Sara reads her notebook, writes down what you just said, helps you one step, and the notebook auto-saves. Repeat.

🛠 `graph.py::run_graph(session_id, message)`:

```python
config = {"configurable": {"thread_id": session_id}}
snapshot = COMPILED_GRAPH.get_state(config)          # load prior checkpoint
base = snapshot.values or build_initial_state(...)   # or start fresh
base["messages"].append({"role": "user", "content": message})
result = COMPILED_GRAPH.invoke(base, config)         # run one turn; checkpoint auto-saves
return result
```

That's the whole runtime loop. No manual persistence, no separate store to keep in sync.

### Step 7 — RAG = retrieve, then write (the only AI step)

🧸 The handbook with a good memory: Sara looks up the right pages **and** glances at what you were just talking about, then explains in plain words.

🛠 `nodes/rag.py`:
1. **Retrieve** — `search_knowledge_base(query)` embeds the question and pulls the top-k chunks from Chroma.
2. **Ground** — build a prompt that contains *only* the retrieved context (so the model answers from the knowledge base, not its imagination).
3. **Remember** — `_recent_history(messages)` passes the recent turns to the model, so follow-ups like *"what's the max benefit?"* resolve against *"…of life insurance"* from the previous turn. (Proof: `test_rag_includes_prior_conversation_as_history`.)
4. **Degrade gracefully** — no API key / network error → a deterministic formatted fallback answer instead of a crash.

The "interrupt-and-resume" magic lives here too: when the router picks `answer_then_resume`, `rag_answer` writes the answer, then the node re-asks the **exact** paused field — and it knows which field from the **checkpointed `current_field`**, not from a string glued onto the answer (which is how the old code faked it).

### Step 8 — Stream it to the browser (SSE)

🧸 Show the words as they're typed, instead of making you wait for the whole paragraph.

🛠 `main.py`: the synchronous graph runs in a thread-pool worker; a thread-local `on_token` callback (`streaming_context.py`) pushes each token onto an `asyncio.Queue`, which the SSE generator yields as `event: token`. Deterministic messages (field prompts, validation errors, the premium) aren't LLM-generated, so they're word-streamed for a consistent feel, then a final `message_complete` event carries the full message + public state.

### Step 9 — Guardrails, per state

🧸 At every station there's a "what if you say something weird" answer ready.

🛠 There is no state without a defined fallback:

| State | Good input | Guardrail (bad input) |
| --- | --- | --- |
| `identify` | product word → start collecting | unknown → re-ask the three options |
| `collect` (number) | in range → store, advance | not a number / out of range → specific error, **same field** |
| `collect` (enum) | allowed value → store | anything else → "choose one of: …" |
| `collect` (text) | clean value → store | a policy question / off-topic → "please answer the requested detail" |
| mid-`collect` + `?` | — | answer via RAG, then **re-ask the same field** |
| `confirm` | accept / adjust / restart | anything else → re-state the three options |
| any | "restart" | wipe progress, back to `identify` |

---

## 4. A real trace (interrupt a quote, then resume)

🧸 You start a quote, ask a side question in the middle, and Sara answers — then picks up on the exact same box. Watch the `field` column never lose its place.

🛠 Captured from the actual compiled graph (RAG stubbed offline):

```
USER: I want a quote for auto insurance
  route=start_quote        step=collect   field=vehicle_year
  BOT: What year is the vehicle? (e.g. 2019)

USER: 2019
  route=collect            step=collect   field=vehicle_make
  BOT: What is the vehicle make? (e.g. Toyota)

USER: what does comprehensive cover?       ← interrupt
  route=answer_then_resume step=collect   field=vehicle_make   ← place is KEPT
  BOT: Comprehensive coverage generally includes non-collision damage …
       Now, back to your auto quote — What is the vehicle make? (e.g. Toyota)

USER: 2019                                  ← "2019" is not a valid make
  route=collect            step=collect   field=vehicle_make
  BOT: Please enter a text value. What is the vehicle make? (e.g. Toyota)

USER: Toyota → Camry → 35 → 0 → standard
  …
  BOT: Your estimated auto premium is $834.60 per year. Reply accept / adjust / restart.
```

The thing that was broken before — keeping your place across a context switch — now falls out of the design for free, because the place lives in durable state and the routing is a rule, not a guess.

---

## 5. Why this method (the trade-off, briefly)

🧸 We let **rules** drive and the **robot** only write.

🛠
- **Deterministic control flow** → reproducible, unit-testable, explainable, cheap (no model call to make a decision), and impossible to "prompt-inject" into changing the flow. Cost: you must enumerate the rules; unforeseen inputs hit a safe default (`rag`).
- **AI only for generation** → flexible, natural answers where flexibility is actually wanted. Cost: must be grounded (RAG) and gracefully degraded, which it is.

The rejected alternative — letting an LLM classify intent each turn — is non-reproducible, costs a call per turn, is hard to explain, and can drift. That drift *was* the original bug.

---

## 6. Run it / test it / extend it

🛠
```bash
# Tests (the spec — 41 of them)
backend/.venv/bin/python -m pytest -q

# Serve
cd backend && .venv/bin/uvicorn main:app --reload
# GET  /health   → liveness
# GET  /debug    → KB + LLM reachability, session count, checkpointer backend
# POST /chat     → {session_id, message}  (SSE stream)
# POST /reset    → {session_id}           (wipe a session)
```

**Extend safely:**
- *Persist across restarts:* swap `MemorySaver()` for a Sqlite/Redis checkpointer in `graph.py` — nothing else changes.
- *Add a product (e.g. travel):* add a `FIELD_SPECS["travel"]` block + a `_calculate_travel` + a `PRODUCT_LABELS["travel"]` entry. No routing changes — the state machine is product-agnostic.
- *Change the conversation policy:* edit the ordered rules in `decide()`. That one function *is* the policy.

---

## 7. File map (where everything lives)

```
backend/
  state.py                     # ChatState shape + initial state
  graph.py                     # checkpointer, deterministic router node, edges, run_graph()
  main.py                      # FastAPI, SSE streaming, /chat /reset /debug, checkpointer-backed view
  streaming_context.py         # thread-local on_token bridge
  nodes/
    router.py                  # decide() — the deterministic rule-card  ← the policy
    identify_product.py        # product detection
    collect_details.py         # FIELD_SPECS + validate/coerce/advance  ← the invariant
    validate_quote.py          # final validation → calculate
    confirm.py                 # accept / adjust / restart
    rag.py                     # retrieve + ground + history + generate (only AI call)
  services/
    vectorstore.py             # ChromaDB + sentence-transformers retrieval
    quote_calculator.py        # deterministic premium math
    llm.py                     # stdlib OpenRouter client (system + history + user; streaming)
tests/
  test_backend_integration.py  # 41 tests: flows, guardrails, persistence, RAG history, pure routing
```

---

## 8. What is deliberately NOT here

🧸 No magic brain we grew ourselves.

🛠 No training, no fine-tuning, no embeddings we fit, no agent that decides its own actions, no LLM in the control path. Two pre-built models are *called*; everything that decides *what happens* is plain, inspectable Python. If you can read `decide()` and `collect_details()`, you can predict every move the system will make — which is exactly the property we wanted.

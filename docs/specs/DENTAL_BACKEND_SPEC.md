# Ivory Dental Backend — Design Spec

**Date:** 2026-06-12 · **Branch:** `feat/dental-backend` · **Status:** Approved decisions baked in
**Decisions locked:** mock-first tools → live later (`TOOLS_MODE`), dental **replaces** insurance, SqliteSaver checkpointer.

> This spec doubles as a learning document. Each section ends with **🎓 Interview
> notes** — the concepts you should be able to explain without looking.

---

## 1. What we're building

Ivory's backend becomes a **dental clinic front-desk agent**: it answers
oral-health questions from a public-domain corpus (NIDCR + CDC), qualifies leads
through deterministic slot-filling, and on explicit confirmation books the
appointment (Cal.com), records the lead (Airtable), and emails a confirmation
(Resend).

The architecture does not change. That is the point of the project: **one
deterministic skeleton, re-skinned onto a new vertical by swapping data, not
logic.**

**🎓 Interview notes** — The one-sentence pitch: *"The LLM is never on the
control-flow path. A rule-based state machine routes every turn; the LLM only
writes answer prose. That's why the bot can't be prompt-injected into skipping
validation or double-booking."* This is the "autonomy with guardrails" pattern
enterprises actually deploy.

## 2. Architecture overview (unchanged skeleton)

```
POST /chat ──► run_graph(session_id, msg)
                  │ checkpointer loads thread (thread_id = session_id)
                  ▼
         START → router (pure rules)
                  ├─► rag_answer          (LLM writes text; resume-aware)
                  ├─► identify_service    (which service to book)
                  ├─► collect_details     (slot-filling + validation)
                  │        └─► validate_intake
                  ├─► confirm             (accept / adjust / restart)
                  │        └─► book_appointment   ← NEW: the only node with side effects
                  └─► END → checkpoint saved atomically → SSE stream
```

**🎓 Interview notes** — LangGraph vocabulary: a `StateGraph` over a TypedDict
state; nodes are pure-ish functions `state -> state`; `add_conditional_edges`
implements the state machine; the **checkpointer** gives durable, per-thread
memory (`thread_id == session_id`) so a session survives interruptions — and
after this phase, restarts (SQLite). LangChain proper only appears at the
leaves (LLM client, vectorstore); orchestration is 100 % LangGraph.

## 3. State schema (renamed end-to-end)

`backend/state.py` — the rename is honest and goes through the wire contract to
the frontend (`types.ts` updates with it):

```python
class ChatState(TypedDict, total=False):
    session_id: str
    messages: list[dict[str, str]]
    mode: str                        # "conversational" | "transactional"
    intent: str
    intake_step: str                 # identify | collect | validate | confirm | booked
    service_type: str | None         # cleaning | consultation | whitening | emergency
    collected_data: dict[str, Any]   # the filled slots
    booking_result: dict[str, Any] | None   # confirmation payload (replaces quote_result)
    pending_question: str | None
    last_error: str | None
    trace_id: str | None
    current_field: str | None
    route: str                       # transient, recomputed every turn
```

`booking_result` (built by the booking node, shown by the UI card):

```python
{
  "service": "cleaning",
  "start_time": "2026-06-18T14:30:00-04:00",
  "patient_name": "Maria Santos",
  "booking_uid": "cal_abc123",        # Cal.com reference ("mock_..." in mock mode)
  "lead_record_id": "recXYZ",         # Airtable reference
  "confirmation_email": "sent",       # sent | failed | skipped
  "summary": "Cleaning on Wed Jun 18, 2:30 PM for Maria Santos"
}
```

## 4. Router (same P1–P6 priority rules, dental keywords)

| Priority | Rule (unchanged logic) | Keyword change |
|---|---|---|
| P1 | restart mid-flow wins | none |
| P2 | explicit flow-start word, any state (also = service switch) | `"quote"` → `"appointment"`, `"book"`, `"schedule"` |
| P3 | awaiting a field: `?` ⇒ answer-then-resume, else collect | none |
| P4 | confirm step ⇒ confirm verbs | none |
| P5 | identify step: service word or affirmation selects | `detect_product` → `detect_service` |
| P6 | idle: explicit booking intent w/o `?` starts flow, else RAG | `QUOTE_INTENT_HINTS` → `BOOKING_INTENT_HINTS`: "come in", "see the dentist", "availability", "slot", "toothache" (emergency fast-path), "cleaning", "whitening" |

**🎓 Interview notes** — Why keywords and not an LLM intent classifier? Because
the router must be **deterministic, testable, and cheap**: the same input
always produces the same route, every rule has a unit test, and routing costs
zero tokens. The honest trade-off: keyword routers have recall limits; the
production-grade upgrade path is a small **fine-tuned classifier or
embedding-similarity intent matcher** — still deterministic at temperature 0,
still off the generation path. Know both sides.

## 5. Service catalog + intake slot schema

`backend/services/catalog.py` (new) defines the four bookable services
(Cal.com event-type IDs live here too). `FIELD_SPECS` becomes intake slots —
same spec format the validator already understands:

```python
INTAKE_FIELDS = [
    {"name": "patient_name",  "prompt": "May I have your full name?",            "type": "str", "min_length": 2},
    {"name": "phone",         "prompt": "What's the best phone number to reach you?", "type": "phone"},
    {"name": "email",         "prompt": "And your email for the confirmation?",  "type": "email"},
    {"name": "patient_status","prompt": "Are you a new or returning patient?",   "type": "str", "allowed": ["new", "returning"]},
    {"name": "preferred_slot","prompt": "What day and time work best? (e.g. 'Wednesday 2:30 PM')", "type": "slot"},
]
```

All services share the intake slots; `service_type` is its own state field
(selected at identify, switchable mid-flow exactly like product switch today).
New validator types: `phone` (digits ≥ 10 after stripping), `email` (regex),
`slot` (parse day/time phrases into a concrete future datetime; reject past).

**🎓 Interview notes** — This is **slot-filling**, the core NLU pattern of
task-oriented dialogue systems (the same formalism as Google's Schema-Guided
Dialogue dataset we eval against). Our extraction is rule-based coercion +
validation; the ML upgrade path is LLM-based extraction **constrained to the
schema** (function-calling / structured output), with the validator still
running after — extraction can be probabilistic as long as acceptance is
deterministic.

## 6. Tools layer (the new architecture lesson)

```
backend/tools/
  base.py        # Protocol interfaces + ToolResult dataclass
  mock.py        # in-memory fakes (default; tests use these)
  live.py        # Cal.com / Airtable / Resend HTTP adapters (Phase 4)
  registry.py    # get_tools() -> selected by TOOLS_MODE=mock|live
```

Interface sketch (`base.py`):

```python
class BookingTool(Protocol):
    def check_availability(self, service: str, start: datetime) -> ToolResult: ...
    def create_booking(self, service: str, start: datetime, name: str, email: str) -> ToolResult: ...

class CrmTool(Protocol):
    def upsert_lead(self, lead: dict) -> ToolResult: ...

class EmailTool(Protocol):
    def send_confirmation(self, to: str, booking: dict) -> ToolResult: ...
```

Rules of the layer:
1. **Only `book_appointment` calls tools.** Validation has already passed and
   the user has explicitly said "accept". No speculative side effects.
2. **Ordered, individually fault-tolerant:** booking → CRM → email. Booking
   failure aborts (state stays at `confirm`, user told the slot was taken /
   service unavailable). CRM/email failures degrade gracefully (booking stands,
   `confirmation_email: "failed"` reported honestly).
3. **Idempotency:** the node writes `booking_uid` into state before the CRM
   step; a retried "accept" with an existing `booking_uid` must not double-book.
4. The graph imports only `registry.get_tools()` — never an SDK.

**🎓 Interview notes** — This is the **tool-calling** story interviewers probe:
*where* do side effects live (one node, post-validation, post-consent), *what
happens on partial failure* (saga-style ordering with graceful degradation),
and *how do you test it* (the Protocol + mock adapters make the whole flow
testable keylessly). Contrast with agentic tool-calling where the LLM chooses
tools at will — and why a front desk must not work that way.

## 7. Data stores

| Store | Role | Schema |
|---|---|---|
| **Chroma** (`backend/vectorstore/`) | RAG corpus | collection `oral_health`; markdown chunks from NIDCR/CDC sources in `backend/knowledge_base/` (~10 files: cleanings, fillings, whitening safety, gum disease, emergencies, kids, FAQ…) with source metadata per chunk |
| **SQLite** (`backend/sessions.db`, new) | LangGraph checkpointer | managed by `langgraph-checkpoint-sqlite`'s `SqliteSaver` — sessions survive restarts |
| **Airtable** `Leads` | CRM (live mode) | `lead_id`, `name`, `phone`, `email`, `service` (select), `preferred_slot` (datetime), `status` (`new→qualified→booked→completed/no-show`), `booking_uid`, `session_id`, `source`, `created_at`, `notes` |
| **Cal.com** | Calendar source of truth | 4 event types = the service catalog; Airtable only mirrors `booking_uid` |

**🎓 Interview notes (the AI/ML core)** — Be able to walk the RAG pipeline:
**chunking** (markdown sections, ~300–500 tokens, overlap), **embedding**
(sentence-transformers, local, free), **retrieval** (cosine top-k=4 into the
prompt), **grounded generation** (the system prompt forbids answering beyond
retrieved context), and **why RAG over fine-tuning** for this use case: the
corpus changes, citations matter, no GPU budget, and hallucination control is a
retrieval problem before it's a generation problem. Note there is **no model
training anywhere** — the LLM stays frozen; we change its inputs, never its
weights.

## 8. Safety, licensing, scope guardrails

- Every RAG answer carries: *"This is general information, not medical advice —
  for anything urgent, call the clinic directly."*
- **Emergency fast-path:** "toothache", "knocked out", "swelling", "bleeding"
  at P6 route to the emergency service intake with the urgent-care disclaimer first.
- Corpus is NIDCR + CDC **public domain only**. Never ingest ADA /
  MouthHealthy.org (all rights reserved) — enforced by a source allowlist in
  `rebuild_knowledge_base.py`.
- The agent discloses it's an AI when asked; never diagnoses; never invents
  availability (mock mode uses a fixed fake calendar so demos are reproducible).

## 9. Evaluation (Phase 6 — but designed now)

Source: Google **Schema-Guided Dialogue** "Services_*/dentist" dialogues.
Three eval suites, run as pytest + a small script:

1. **Router accuracy** — utterance → expected route (target ≥ 95 % on a
   curated 100-utterance set; failures become new keyword rules or documented limits).
2. **Slot extraction** — SGD turns → expected `collected_data` deltas.
3. **RAG faithfulness** — 20 questions with known corpus answers; grade
   groundedness (answer must cite retrieved chunk content; spot-check + LLM-judge).

**🎓 Interview notes** — Evals are the highest-signal thing a junior AI engineer
can show. The vocabulary: golden sets, deterministic vs LLM-judged metrics,
regression gating in CI ("the router eval is a unit test — it can never silently
get worse").

## 10. Build phases

| Phase | Delivers | Proof |
|---|---|---|
| 1 | SqliteSaver + service catalog + intake slots + router/identify renames | rewritten test suite green, keyless |
| 2 | `validate_intake` + confirm verbs against intake | flow tests green |
| 3 | tools layer (mock) + `book_appointment` node + failure paths | booking tests green, idempotency test |
| 4 | live adapters (Cal.com, Airtable, Resend) behind `TOOLS_MODE=live` | manual E2E + recorded smoke test |
| 5 | NIDCR/CDC corpus + disclaimer + emergency fast-path | rebuilt index, RAG answers grounded |
| 6 | eval suites (router / slots / RAG) | eval report in repo |
| 7 | frontend copy pass (starter cards, prompts, quote card → booking card) | Playwright walk |

Phases 1–3 are one implementation plan (`docs/plans/DENTAL_BACKEND_PHASE1_PLAN.md`);
4–7 get their own plans so each lands as working software.

## 11. Out of scope (v1)

Payments, reminders/no-show automation, multi-clinic/multi-provider calendars,
HIPAA posture (demo collects only contact info; no health history fields),
LLM-based slot extraction (documented as upgrade path), n8n alternative build.

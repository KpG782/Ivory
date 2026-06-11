# Dental Backend Phases 1–3 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the deterministic insurance engine into the dental intake engine — durable sessions (SqliteSaver), dental service catalog + intake slots, dental router, mock tools layer, and the `book_appointment` node — all keyless and fully tested.

**Architecture:** Per `docs/specs/DENTAL_BACKEND_SPEC.md`. The graph skeleton (`router → handler → END`, checkpointer-as-memory) is untouched; we swap schemas, keywords, the terminal node, and add `backend/tools/`.

**Tech Stack:** Python 3.12, LangGraph, `langgraph-checkpoint-sqlite`, pytest (real TDD — the backend has a suite), FastAPI untouched except field names in snapshots.

**Teaching mode:** Each task ends with a **🎓 checkpoint** — say it out loud before moving on; these are the interview explanations.

**Working agreement:** TDD per task (write/adjust the failing test first). The existing `tests/test_backend_integration.py` tests insurance flows; each task migrates the tests it touches rather than deleting coverage. Run suite: `backend/.venv/bin/python -m pytest tests/ -q` from repo root.

---

### Task 1: Durable sessions — SqliteSaver

**Files:** Modify `backend/graph.py`; Modify `backend/requirements.txt`; Test `tests/test_backend_integration.py` (reset fixture only)

- [ ] **Step 1:** `backend/.venv/bin/pip install langgraph-checkpoint-sqlite` and add `langgraph-checkpoint-sqlite` to `backend/requirements.txt`.
- [ ] **Step 2:** In `graph.py`, replace the MemorySaver wiring:

```python
import os
from langgraph.checkpoint.sqlite import SqliteSaver

SESSIONS_DB = os.environ.get("SESSIONS_DB_PATH", os.path.join(os.path.dirname(__file__), "sessions.db"))

def _make_checkpointer():
    if os.environ.get("SESSIONS_BACKEND", "sqlite") == "memory":
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
    import sqlite3
    conn = sqlite3.connect(SESSIONS_DB, check_same_thread=False)
    return SqliteSaver(conn)

_checkpointer = _make_checkpointer()
```

`reset_all()` rebuilds via `_make_checkpointer()` too. Tests set `SESSIONS_BACKEND=memory` (add to `pytest.ini`: `env =` via `pytest-env`, or set in a session fixture with `os.environ.setdefault`) so the suite stays hermetic. Add `backend/sessions.db` to `.gitignore`.

- [ ] **Step 3:** Manual proof: start uvicorn, send a message, restart uvicorn, send another message in the same session — state resumes. Run suite → green.
- [ ] **Step 4:** Commit: `git commit -m "feat(backend): durable sessions via SqliteSaver"`

**🎓 checkpoint:** "LangGraph checkpointers serialize the state per `thread_id` after every invocation. Swapping MemorySaver→SqliteSaver changed zero business logic — persistence is a deployment concern, which is exactly why the checkpointer abstraction exists. Redis is the same one-line swap for horizontal scale."

---

### Task 2: Service catalog + `detect_service`

**Files:** Create `backend/services/catalog.py`; Rename `backend/nodes/identify_product.py` → `identify_service.py`; Test: new `tests/test_router_dental.py`

- [ ] **Step 1:** Write failing tests:

```python
from services.catalog import SERVICES, detect_service

def test_detect_service_by_keyword():
    assert detect_service("i need a cleaning") == "cleaning"
    assert detect_service("my tooth is killing me") == "emergency"
    assert detect_service("teeth whitening please") == "whitening"
    assert detect_service("just a checkup consult") == "consultation"

def test_detect_service_none_for_unrelated():
    assert detect_service("what are your hours?") is None
```

- [ ] **Step 2:** `backend/services/catalog.py`:

```python
SERVICES: dict[str, dict] = {
    "cleaning":     {"label": "Cleaning & checkup", "duration_min": 45, "cal_event_type": "cleaning-45"},
    "consultation": {"label": "Consultation",       "duration_min": 30, "cal_event_type": "consult-30"},
    "whitening":    {"label": "Whitening",          "duration_min": 60, "cal_event_type": "whitening-60"},
    "emergency":    {"label": "Emergency visit",    "duration_min": 30, "cal_event_type": "emergency-30"},
}

_KEYWORDS = {
    "cleaning": ("cleaning", "clean my teeth", "checkup", "check-up", "hygiene"),
    "consultation": ("consultation", "consult", "second opinion", "new patient exam"),
    "whitening": ("whitening", "whiten", "bleaching"),
    "emergency": ("emergency", "toothache", "tooth ache", "killing me", "knocked out",
                  "broken tooth", "chipped", "swelling", "bleeding gums", "severe pain"),
}

def detect_service(text: str) -> str | None:
    lowered = text.lower()
    for service, needles in _KEYWORDS.items():
        if any(n in lowered for n in needles):
            return service
    return None
```

(Order matters: dict order is checked top-down; "emergency cleaning" → cleaning is acceptable; if disputed, check emergency first — pick one and test it.)

- [ ] **Step 3:** `git mv backend/nodes/identify_product.py backend/nodes/identify_service.py`; inside, `identify_product` → `identify_service`, `detect_product` now imports `detect_service` from the catalog and the node prompt becomes: *"Which service would you like to book: cleaning, consultation, whitening — or is this an emergency?"* Update imports in `graph.py` and `router.py`.
- [ ] **Step 4:** Run new tests → pass; full suite will fail on renames — that's Task 3's job. Commit at the end of Task 3 instead if preferred, otherwise commit the catalog alone (it's additive): `feat(backend): dental service catalog`.

**🎓 checkpoint:** "The catalog is the single source of truth for what's bookable — router keywords, intake prompts, and Cal.com event types all derive from it. Adding a service is a data change, not a code change."

---

### Task 3: State rename (end-to-end, including the wire contract)

**Files:** Modify `backend/state.py`, `backend/graph.py`, `backend/nodes/*.py`, `backend/main.py`, `tests/*.py`, `frontend/src/types.ts`, `frontend/src/App.tsx`, `frontend/src/hooks/useChat.ts`

- [ ] **Step 1:** Mechanical rename map (apply with grep-verified sed across backend, tests, and frontend; review the diff before committing):

| Old | New |
|---|---|
| `insurance_type` | `service_type` |
| `quote_step` | `intake_step` |
| `quote_result` | `booking_result` |
| `has_quote_result` | `has_booking_result` |
| `start_quote` (route) | `start_intake` |
| `_reset_quote_progress` | `_reset_intake_progress` |

- [ ] **Step 2:** Frontend ripple (tsc is the checklist): `types.ts` `SessionSnapshot` + `QuoteResult` → `BookingResult` (keep the export name `QuoteResult` as a deprecated alias for one commit if it shortens the diff — then remove), `App.tsx` `flowChipLabel`/`progressFraction`/`hasQuoteResult` props, `useChat.ts` snapshot literals + `extractQuoteResult` payload keys (`booking_result`).
- [ ] **Step 3:** `cd frontend && npx tsc --noEmit` clean; backend suite: insurance-flow tests now fail on *content* (they speak insurance) — mark the migration: each failing test either (a) renames trivially (state-shape tests), or (b) is rewritten in Tasks 4–6 (flow tests). Park (b) with `@pytest.mark.skip(reason="migrating to dental in task N")` — **every skip must be removed by end of Task 6.**
- [ ] **Step 4:** Commit: `refactor: rename quote domain to intake/booking across the stack`

**🎓 checkpoint:** "The state schema *is* the API. Renaming it end-to-end (backend TypedDict → SSE payload → frontend types) in one commit keeps the contract honest — the alternative, translation layers, is how systems rot."

---

### Task 4: Dental router

**Files:** Modify `backend/nodes/router.py`; Test `tests/test_router_dental.py`

- [ ] **Step 1:** Failing tests (the P-rules, dental):

```python
from nodes.router import decide

IDLE = {"mode": "conversational", "intake_step": "identify", "current_field": None}

def test_book_starts_intake():
    assert decide(dict(IDLE), "I'd like to book an appointment") == "start_intake"

def test_emergency_word_starts_intake_from_idle():
    assert decide(dict(IDLE), "I have a terrible toothache") == "start_intake"

def test_question_stays_rag():
    assert decide(dict(IDLE), "Does whitening damage enamel?") == "rag"

def test_midflow_question_resumes():
    state = {"mode": "transactional", "intake_step": "collect", "current_field": "phone"}
    assert decide(state, "wait, do you take walk-ins?") == "answer_then_resume"

def test_midflow_value_collects():
    state = {"mode": "transactional", "intake_step": "collect", "current_field": "phone"}
    assert decide(state, "09171234567") == "collect"
```

Note the nuance: `"Does whitening damage enamel?"` contains a service keyword
but has `?` → must stay RAG. P6 already requires `"?" not in text`; the
emergency-keyword test must respect the same guard (P2/P6 ordering test it).

- [ ] **Step 2:** Implement: P2 trigger words → `("appointment", "book", "schedule")`; `QUOTE_INTENT_HINTS` → `BOOKING_INTENT_HINTS = ("price", "pricing", "availability", "available", "come in", "see the dentist", "slot", "walk in")` **plus** `detect_service(text)` as an idle-intent signal (P6 becomes: no `?` and (hint or service word) → `start_intake`). P5 uses `detect_service`. Docstring route names updated.
- [ ] **Step 3:** Tests pass; commit `feat(backend): dental routing rules`.

**🎓 checkpoint:** "Routing is an ordered rule cascade — P1 restart > P2 explicit booking > P3 pending field > P4 confirm > P5 identify > P6 idle intent. Every priority inversion bug we ever had became a test at the exact priority boundary. A '?' while a field is pending is the entire interruption feature."

---

### Task 5: Intake slots + new validator types

**Files:** Modify `backend/nodes/collect_details.py`; Test `tests/test_intake_slots.py`

- [ ] **Step 1:** Failing tests:

```python
from nodes.collect_details import collect_details

def make_state(field, **collected):
    return {"mode": "transactional", "intake_step": "collect", "service_type": "cleaning",
            "current_field": field, "collected_data": dict(collected), "messages": [
                {"role": "user", "content": "x"}]}

def test_phone_accepts_digits_with_punctuation():
    state = make_state("phone", patient_name="Maria Santos")
    out = collect_details(state, "(917) 555-0144")
    assert out["collected_data"]["phone"] == "9175550144"

def test_phone_rejects_short():
    state = make_state("phone", patient_name="Maria Santos")
    out = collect_details(state, "12345")
    assert "phone" not in out["collected_data"]          # invalid input never advances
    assert out["current_field"] == "phone"

def test_email_validated():
    state = make_state("email", patient_name="M S", phone="9175550144")
    out = collect_details(state, "maria at example dot com")
    assert out["current_field"] == "email"

def test_slot_parses_weekday_time():
    state = make_state("preferred_slot", patient_name="M S", phone="9175550144",
                       email="m@example.com", patient_status="new")
    out = collect_details(state, "Wednesday 2:30 pm")
    assert out["collected_data"]["preferred_slot"].endswith(":30:00")
    assert out["intake_step"] == "validate"              # last slot filled → advance
```

- [ ] **Step 2:** Replace `FIELD_SPECS` with the shared `INTAKE_FIELDS` list from the spec (§5) keyed per service (`FIELD_SPECS = {s: INTAKE_FIELDS for s in SERVICES}` keeps the existing per-service lookup code working). Delete `_merge_auto_*` (insurance-only compact input) and the `LOCATION_DENYLIST`.
- [ ] **Step 3:** Add coercers in `_coerce_value`:

```python
if field_type == "phone":
    digits = re.sub(r"\D", "", value)
    if len(digits) < 10 or len(digits) > 15:
        return None, "That phone number doesn't look complete — please include the area code."
    return digits, None

if field_type == "email":
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", value.strip()):
        return None, "That email doesn't look right — could you re-type it? (e.g. maria@example.com)"
    return value.strip().lower(), None

if field_type == "slot":
    parsed = parse_slot_phrase(value)        # see below
    if parsed is None:
        return None, "I couldn't read that time — try something like 'Wednesday 2:30 PM'."
    if parsed <= datetime.now(UTC):
        return None, "That time is in the past — what's the next day and time that works?"
    return parsed.isoformat(), None
```

`parse_slot_phrase` (same file): weekday-name + `H[:MM] am/pm` regex → next
occurrence of that weekday at that time (UTC for v1; timezone handling is a
documented Phase 4 concern with Cal.com). ~25 lines, fully unit-tested.

- [ ] **Step 4:** Tests pass; remove the now-covered skips; commit `feat(backend): dental intake slots with phone/email/slot validation`.

**🎓 checkpoint:** "The invariant that survives every refactor: **invalid input never advances `current_field`**. Extraction can be dumb or smart, but acceptance is deterministic — that single rule is why the flow can't be talked into a corrupt state."

---

### Task 6: `validate_intake` + confirm verbs

**Files:** Rename `backend/nodes/validate_quote.py` → `validate_intake.py`; Modify `backend/nodes/confirm.py`; Delete `backend/services/quote_calculator.py`; Test `tests/test_intake_flow.py`

- [ ] **Step 1:** Failing flow test (end-to-end through `run_graph`, like the existing integration tests):

```python
def test_full_intake_reaches_confirm(client):
    sid = "t-intake-1"
    send(client, sid, "book a cleaning")
    send(client, sid, "Maria Santos")
    send(client, sid, "9175550144")
    send(client, sid, "maria@example.com")
    send(client, sid, "new")
    reply = send(client, sid, "Wednesday 2:30 pm")
    assert "confirm" in snapshot(client, sid)["intake_step"]
    assert "Maria Santos" in reply and "cleaning" in reply.lower()
```

- [ ] **Step 2:** `validate_intake`: re-runs the field validators over
`collected_data` (defense in depth, same as today), then composes the
confirmation summary message: *"Here's what I have: **Cleaning & checkup** for
**Maria Santos**, Wednesday Jun 18 at 2:30 PM, phone 9175550144,
confirmation to maria@example.com. Reply **accept** to book it, **adjust** to
change something, or **restart**."* Sets `intake_step="confirm"`. No calculator —
delete `quote_calculator.py` and its imports.
- [ ] **Step 3:** `confirm.py`: `adjust` and `restart` unchanged (verbs + reset);
`accept` no longer finalizes inline — it returns state routed onward to
`book_appointment` (Task 7 wires the edge; until then `accept` sets
`intake_step="booked"` with a placeholder summary so this task lands green).
- [ ] **Step 4:** Suite green (all Task-3 skips now removed). Commit:
`feat(backend): intake validation and confirmation summary`.

**🎓 checkpoint:** "Validate runs twice — per-field at collection and whole-record before confirm. Cheap, and it means the confirm summary can never display data that wouldn't book."

---

### Task 7: Mock tools layer + `book_appointment` node

**Files:** Create `backend/tools/{__init__,base,mock,registry}.py`; Create `backend/nodes/book_appointment.py`; Modify `backend/graph.py`, `backend/nodes/confirm.py`; Test `tests/test_booking.py`

- [ ] **Step 1:** Failing tests:

```python
def test_accept_books_and_reports(client):
    sid = drive_to_confirm(client)                      # helper from task 6 test
    reply = send(client, sid, "accept")
    snap = snapshot(client, sid)
    assert snap["intake_step"] == "booked"
    assert snap["has_booking_result"] is True
    assert "booked" in reply.lower() and "maria@example.com" in reply

def test_accept_is_idempotent(client):
    sid = drive_to_confirm(client)
    send(client, sid, "accept")
    uid1 = booking_uid(client, sid)
    send(client, sid, "accept")                          # user double-sends
    assert booking_uid(client, sid) == uid1              # no double-booking

def test_unavailable_slot_keeps_confirm_state(client, monkeypatch):
    # mock tool returns unavailable for this start time
    sid = drive_to_confirm(client, slot="Friday 2:30 pm")  # mock calendar blocks Fridays
    reply = send(client, sid, "accept")
    assert snapshot(client, sid)["intake_step"] == "confirm"
    assert "taken" in reply.lower() or "another time" in reply.lower()
```

- [ ] **Step 2:** `base.py` — the Protocols + `ToolResult(ok: bool, data: dict, error: str | None)` exactly as in spec §6. `mock.py` — in-memory: `MockBooking` (fixed fake calendar: weekdays 9:00–17:00 free **except Fridays** — gives tests a deterministic "unavailable" case; `create_booking` returns `mock_<uuid8>` and records it), `MockCrm` (list of leads, upsert by `session_id`), `MockEmail` (records sends, always ok). `registry.py`:

```python
import os
from tools import base, mock

def get_tools() -> base.ToolBundle:        # ToolBundle = NamedTuple(booking, crm, email)
    mode = os.environ.get("TOOLS_MODE", "mock")
    if mode == "mock":
        return mock.bundle()
    from tools import live                  # Phase 4
    return live.bundle()
```

- [ ] **Step 3:** `nodes/book_appointment.py` — the spec §6 sequence with the
three failure rules (abort on booking failure; degrade on CRM/email failure;
short-circuit to success if `booking_result.booking_uid` already exists =
idempotency). Composes the final message honestly, including
*"…though the confirmation email didn't go through — please save this:
\<summary\>"* on email failure.
- [ ] **Step 4:** Wire the graph: `confirm` on accept sets `route="book"`;
`_route_after_confirm` gains `"book_appointment"`; new node → END. The
booking node is the ONLY importer of `registry.get_tools()`.
- [ ] **Step 5:** Full suite green. Commit:
`feat(backend): mock tools layer and book_appointment node`.
- [ ] **Step 6:** Push branch: `git push origin feat/dental-backend`.

**🎓 checkpoint:** "Side effects live in one node, behind three rules: post-validation, post-consent, idempotent. The mock adapters aren't test hacks — they're the same interface production uses, which is what makes 'works without API keys' true at the architectural level, not the marketing level."

---

## Self-review

- Spec coverage: §3→T3, §4→T4, §5→T5, §6→T7, §7(SQLite)→T1, catalog→T2, validate/confirm→T6. Phases 4–7 intentionally out (separate plans). ✓
- No placeholders: code or exact rename maps everywhere; mock calendar rule (Fridays blocked) is concrete. ✓
- Type consistency: `intake_step`/`service_type`/`booking_result` used consistently from T3 onward; `ToolBundle` defined T7 Step 2 before use in Step 3. ✓

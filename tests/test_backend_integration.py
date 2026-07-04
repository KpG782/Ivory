from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import main
from services.vectorstore import RetrievedChunk

# Load-bearing copy asserted literally across the suite (spec section 9.3).
SERVICE_MENU = (
    "Which type of visit would you like to set up: a cleaning, "
    "an emergency visit, or a cosmetic consultation?"
)
PATIENT_NAME_PROMPT = "What's the patient's full name? (e.g. Maria Santos)"
CONTACT_EMAIL_PROMPT = "What email should we use for confirmations? (e.g. maria@example.com)"
LAST_VISIT_YEAR_PROMPT = "What year was your last dental visit? (e.g. 2024)"
INSURANCE_STATUS_PROMPT = (
    "Do you have dental insurance, or are you paying out of pocket? (insured or self-pay)"
)
PREFERRED_TIME_PROMPT = "What time of day works best: morning, afternoon, or evening?"
CONTACT_PHONE_PROMPT = "What phone number can we reach you at? (e.g. 555-201-7788)"
ISSUE_TYPE_PROMPT = "What's the problem: a toothache, chipped tooth, swelling, or a lost filling?"
PAIN_LEVEL_PROMPT = "On a scale of 0 to 10, how bad is the pain right now?"

CLEANING_FLOW = [
    "I want to book a cleaning",
    "Maria Santos",
    "maria@example.com",
    "2024",
    "insured",
    "morning",
]
EMERGENCY_FLOW = [
    "I need to book an emergency visit",
    "Ken Garcia",
    "555-201-7788",
    "toothache",
    "7",
    "insured",
]
COSMETIC_FLOW = [
    "I want to book a cosmetic consultation",
    "Maria Santos",
    "maria@example.com",
    "veneers",
    "standard",
    "flexible",
]

# Integration env keys are scrubbed in the base fixture so front-desk clients
# stay in dry-run mode (no network) unless a test explicitly configures them.
INTEGRATION_ENV_VARS = (
    "AIRTABLE_API_KEY",
    "AIRTABLE_BASE_ID",
    "AIRTABLE_TABLE_NAME",
    "CALCOM_API_KEY",
    "CALCOM_EVENT_TYPE_ID",
    "RESEND_API_KEY",
    "RESEND_FROM",
)


def _dental_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        id="kb-1",
        score=0.99,
        source="02_routine_checkups_and_cleanings.md",
        title="Routine Checkups and Cleanings",
        content=(
            "A routine dental cleaning includes removing plaque and tartar buildup, "
            "polishing the teeth, and an exam to check for early signs of tooth decay "
            "or gum disease."
        ),
        metadata={
            "source": "02_routine_checkups_and_cleanings.md",
            "title": "Routine Checkups and Cleanings",
        },
    )


def _parse_sse_body(body: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for raw_event in body.strip().split("\n\n"):
        if not raw_event.strip():
            continue
        event_name = "message"
        data_lines: list[str] = []
        for line in raw_event.splitlines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())
        payload = "\n".join(data_lines)
        events.append(
            {
                "event": event_name,
                "data": json.loads(payload) if payload else None,
            }
        )
    return events


def _post_chat(client: TestClient, session_id: str, message: str) -> list[dict[str, Any]]:
    response = client.post("/chat", json={"session_id": session_id, "message": message})
    assert response.status_code == 200
    return _parse_sse_body(response.text)


def _run_flow(client: TestClient, session_id: str, messages: list[str]) -> list[dict[str, Any]]:
    final_events: list[dict[str, Any]] = []
    for message in messages:
        final_events = _post_chat(client, session_id, message)
    return final_events


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import nodes.rag as rag

    # Disable rate limiting so the test suite does not hit per-IP limits.
    # _is_rate_limit_disabled() reads this env var at request time, so
    # monkeypatch.setenv is effective even though main.py is already imported.
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

    # Guarantee the front-desk integrations run in dry-run mode (no network)
    # regardless of any locally configured .env values.
    for env_var in INTEGRATION_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)

    main.SESSION_STORE.clear()

    # Routing is deterministic (no LLM), so there is no classifier to stub. We
    # only stub the RAG LLM client + retrieval so tests are hermetic/offline.
    monkeypatch.setattr(rag, "_build_client_or_none", lambda: None)
    monkeypatch.setattr(
        rag,
        "search_knowledge_base",
        lambda *args, **kwargs: [_dental_chunk()],
    )

    with TestClient(main.app) as test_client:
        yield test_client

    main.SESSION_STORE.clear()


# ── Health + reset ────────────────────────────────────────────────────────────

def test_health_endpoint_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_reset_endpoint_reinitializes_session(client: TestClient) -> None:
    response = client.post("/reset", json={"session_id": "reset-session"})

    assert response.status_code == 200
    assert response.json() == {"status": "reset", "session_id": "reset-session"}
    assert main.SESSION_STORE["reset-session"]["mode"] == "conversational"
    assert main.SESSION_STORE["reset-session"]["intake_step"] == "identify"


# ── RAG mode ──────────────────────────────────────────────────────────────────

def test_chat_question_streams_sse_events(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={"session_id": "question-session", "message": "What happens during a dental checkup?"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse_body(response.text)

    assert events[0]["event"] == "token"
    assert events[-1]["event"] == "message_complete"
    assert "cleaning" in events[-1]["data"]["message"].lower()
    assert events[-1]["data"]["session"]["mode"] == "conversational"
    assert events[-1]["data"]["session"]["intake_step"] == "identify"


def test_rag_fallback_returns_clean_direct_answer_without_llm(client: TestClient) -> None:
    events = _post_chat(client, "fallback-rag-session", "What does a routine cleaning include?")

    message = events[-1]["data"]["message"].lower()
    assert "routine dental cleaning includes removing plaque" in message
    assert "based on the knowledge base" not in message


# ── Happy paths: cleaning (through accept), emergency, cosmetic ───────────────

def test_cleaning_intake_flow_returns_visit_estimate(client: TestClient) -> None:
    final_events = _run_flow(client, "cleaning-session", CLEANING_FLOW)

    assert final_events[-1]["event"] == "message_complete"
    payload = final_events[-1]["data"]
    estimate = payload["visit_estimate"]
    assert estimate["service_type"] == "cleaning"
    assert estimate["insurance_status"] == "insured"
    assert estimate["preferred_time"] == "morning"
    assert estimate["currency"] == "USD"
    assert estimate["summary"] == "Routine exam & cleaning for Maria Santos"
    assert 0 < estimate["estimate_low"] < estimate["estimate_high"]
    assert "estimated cleaning visit cost" in payload["message"].lower()
    assert f"${estimate['estimate_low']:.2f}–${estimate['estimate_high']:.2f}" in payload["message"]
    assert payload["session"]["mode"] == "transactional"
    assert payload["session"]["intake_step"] == "confirm"
    assert payload["session"]["has_visit_estimate"] is True


def test_cleaning_accept_reports_front_desk_dry_run_actions(client: TestClient) -> None:
    session_id = "cleaning-accept-session"
    _run_flow(client, session_id, CLEANING_FLOW)

    events = _post_chat(client, session_id, "accept")
    message = events[-1]["data"]["message"]

    assert "Confirmed." in message
    assert "Front desk actions:" in message
    airtable_line = "- Airtable CRM: Airtable (demo mode): lead captured locally"
    calcom_line = "- Cal.com booking: Cal.com (demo mode): booking request recorded locally"
    resend_line = "- Email confirmation: Resend (demo mode): confirmation email drafted locally"
    assert airtable_line in message
    assert calcom_line in message
    assert resend_line in message
    # The three lines render in a fixed order after the header.
    assert message.index("Front desk actions:") < message.index(airtable_line)
    assert message.index(airtable_line) < message.index(calcom_line) < message.index(resend_line)
    assert events[-1]["data"]["session"]["mode"] == "conversational"
    assert events[-1]["data"]["session"]["intake_step"] == "identify"


def test_emergency_intake_flow_returns_visit_estimate(client: TestClient) -> None:
    final_events = _run_flow(client, "emergency-session", EMERGENCY_FLOW)

    payload = final_events[-1]["data"]
    estimate = payload["visit_estimate"]
    assert estimate["service_type"] == "emergency"
    assert estimate["issue_type"] == "toothache"
    assert estimate["pain_level"] == 7
    # Deterministic fee schedule: 110 * 1.35 (toothache) * 1.14 (pain 7) * 0.5 (insured).
    assert estimate["estimate_low"] == 71.95
    assert estimate["estimate_high"] == 105.81
    assert "estimated emergency visit cost" in payload["message"].lower()
    assert payload["session"]["intake_step"] == "confirm"


def test_cosmetic_intake_flow_returns_visit_estimate(client: TestClient) -> None:
    final_events = _run_flow(client, "cosmetic-session", COSMETIC_FLOW)

    payload = final_events[-1]["data"]
    estimate = payload["visit_estimate"]
    assert estimate["service_type"] == "cosmetic"
    assert estimate["treatment"] == "veneers"
    assert estimate["budget_band"] == "standard"
    assert estimate["timeline"] == "flexible"
    # Deterministic fee schedule: 1400 (veneers) * 1.0 (standard) * 0.95 (flexible) ± 15%.
    assert estimate["estimate_low"] == 1130.5
    assert estimate["estimate_high"] == 1529.5
    assert "estimated cosmetic consultation cost" in payload["message"].lower()
    assert payload["session"]["intake_step"] == "confirm"


def test_visit_estimates_are_deterministic_for_identical_inputs(client: TestClient) -> None:
    first = _run_flow(client, "deterministic-a", CLEANING_FLOW)
    second = _run_flow(client, "deterministic-b", CLEANING_FLOW)

    assert first[-1]["data"]["visit_estimate"] == second[-1]["data"]["visit_estimate"]


# ── Interruption + exact resume ───────────────────────────────────────────────

def test_mid_flow_question_preserves_intake_progress(client: TestClient) -> None:
    session_id = "interrupt-session"

    start_events = _post_chat(client, session_id, "I want to book a cleaning")
    assert start_events[-1]["data"]["message"] == PATIENT_NAME_PROMPT

    _post_chat(client, session_id, "Maria Santos")

    question_events = _post_chat(client, session_id, "What does a routine cleaning include?")
    question_message = question_events[-1]["data"]["message"]

    assert "routine dental cleaning includes" in question_message.lower()
    expected_resume = (
        "\n\nNow, back to your cleaning visit intake — "
        f"{CONTACT_EMAIL_PROMPT}"
    )
    assert question_message.endswith(expected_resume)
    assert main.SESSION_STORE[session_id]["current_field"] == "contact_email"
    assert main.SESSION_STORE[session_id]["collected_data"]["patient_name"] == "Maria Santos"
    assert question_events[-1]["data"]["session"]["intake_step"] == "collect"

    resume_events = _post_chat(client, session_id, "maria@example.com")

    assert resume_events[-1]["data"]["message"] == LAST_VISIT_YEAR_PROMPT
    assert main.SESSION_STORE[session_id]["collected_data"]["contact_email"] == "maria@example.com"


def test_mid_intake_question_answers_then_resumes_first_field(client: TestClient) -> None:
    session_id = "mid-intake-question-session"

    _post_chat(client, session_id, "I want to book a cleaning")

    events = _post_chat(client, session_id, "What does a routine cleaning include?")
    payload = events[-1]["data"]

    assert "routine dental cleaning includes" in payload["message"].lower()
    assert payload["message"].endswith(
        f"\n\nNow, back to your cleaning visit intake — {PATIENT_NAME_PROMPT}"
    )
    assert payload["session"]["mode"] == "transactional"
    assert payload["session"]["intake_step"] == "collect"


# ── Flow-start guards + compact input ─────────────────────────────────────────

def test_bare_year_reply_stays_in_intake_flow(client: TestClient) -> None:
    """A bare value like "2024" is always stored as the field, never re-routed."""
    session_id = "bare-year-session"

    _post_chat(client, session_id, "I want to book a cleaning")
    _post_chat(client, session_id, "Maria Santos")
    _post_chat(client, session_id, "maria@example.com")
    events = _post_chat(client, session_id, "2024")

    assert events[-1]["data"]["message"] == INSURANCE_STATUS_PROMPT
    assert events[-1]["data"]["session"]["mode"] == "transactional"
    assert events[-1]["data"]["session"]["intake_step"] == "collect"
    assert main.SESSION_STORE[session_id]["collected_data"]["last_visit_year"] == 2024


def test_explicit_booking_request_starts_identify_menu(client: TestClient) -> None:
    events = _post_chat(client, "intake-start-session", "I'd like to book an appointment")
    payload = events[-1]["data"]

    assert payload["message"] == SERVICE_MENU
    assert payload["session"]["mode"] == "transactional"
    assert payload["session"]["intake_step"] == "identify"
    assert payload["session"]["service_type"] is None


def test_compact_cleaning_details_fill_multiple_fields(client: TestClient) -> None:
    session_id = "compact-cleaning-session"

    start_events = _post_chat(client, session_id, "I want to book a cleaning")
    assert start_events[-1]["data"]["message"] == PATIENT_NAME_PROMPT

    events = _post_chat(client, session_id, "Maria Santos, maria@example.com, 2024, insured, morning")

    payload = events[-1]["data"]
    assert "estimated cleaning visit cost" in payload["message"].lower()
    assert payload["visit_estimate"]["service_type"] == "cleaning"
    assert payload["session"]["intake_step"] == "confirm"
    assert payload["session"]["has_visit_estimate"] is True

    state = main.SESSION_STORE[session_id]
    assert state["collected_data"]["patient_name"] == "Maria Santos"
    assert state["collected_data"]["contact_email"] == "maria@example.com"
    assert state["collected_data"]["last_visit_year"] == 2024
    assert state["collected_data"]["insurance_status"] == "insured"
    assert state["collected_data"]["preferred_time"] == "morning"


# ── Identify step: menu + aliases ─────────────────────────────────────────────

def test_checkup_alias_selects_cleaning_service(client: TestClient) -> None:
    session_id = "checkup-alias-session"

    _post_chat(client, session_id, "I'd like to book an appointment")
    events = _post_chat(client, session_id, "checkup")

    payload = events[-1]["data"]
    assert payload["message"] == PATIENT_NAME_PROMPT
    assert payload["session"]["mode"] == "transactional"
    assert payload["session"]["intake_step"] == "collect"
    assert payload["session"]["service_type"] == "cleaning"


def test_urgent_alias_selects_emergency_service(client: TestClient) -> None:
    session_id = "urgent-alias-session"

    _post_chat(client, session_id, "I'd like to book an appointment")
    events = _post_chat(client, session_id, "urgent")

    payload = events[-1]["data"]
    assert payload["message"] == PATIENT_NAME_PROMPT
    assert payload["session"]["mode"] == "transactional"
    assert payload["session"]["intake_step"] == "collect"
    assert payload["session"]["service_type"] == "emergency"


def test_question_at_identify_step_reasks_service_menu(client: TestClient) -> None:
    session_id = "identify-question-session"

    _post_chat(client, session_id, "I'd like to book an appointment")
    events = _post_chat(client, session_id, "What are your hours?")

    payload = events[-1]["data"]
    assert payload["message"].endswith(f"\n\n{SERVICE_MENU}")
    assert payload["session"]["mode"] == "transactional"
    assert payload["session"]["intake_step"] == "identify"
    assert payload["session"]["service_type"] is None


# ── Invalid-input matrix ──────────────────────────────────────────────────────

def test_invalid_numeric_input_reprompts_without_advancing(client: TestClient) -> None:
    session_id = "invalid-numeric-session"

    _post_chat(client, session_id, "I want to book a cleaning")
    _post_chat(client, session_id, "Maria Santos")
    _post_chat(client, session_id, "maria@example.com")
    events = _post_chat(client, session_id, "abc")

    message = events[-1]["data"]["message"]
    assert message == f"Please enter a whole number. {LAST_VISIT_YEAR_PROMPT}"
    assert main.SESSION_STORE[session_id]["current_field"] == "last_visit_year"
    assert "last_visit_year" not in main.SESSION_STORE[session_id]["collected_data"]


def test_future_last_visit_year_is_rejected_immediately(client: TestClient) -> None:
    session_id = "future-year-session"

    _post_chat(client, session_id, "I want to book a cleaning")
    _post_chat(client, session_id, "Maria Santos")
    _post_chat(client, session_id, "maria@example.com")
    events = _post_chat(client, session_id, "2031")

    message = events[-1]["data"]["message"]
    assert "last dental visit year must be between 1901" in message.lower()
    assert message.endswith(LAST_VISIT_YEAR_PROMPT)
    assert main.SESSION_STORE[session_id]["intake_step"] == "collect"
    assert main.SESSION_STORE[session_id]["current_field"] == "last_visit_year"
    assert "last_visit_year" not in main.SESSION_STORE[session_id]["collected_data"]


def test_negative_pain_level_is_rejected_before_estimate(client: TestClient) -> None:
    session_id = "negative-pain-session"
    _run_flow(client, session_id, EMERGENCY_FLOW[:4])

    events = _post_chat(client, session_id, "-1")
    message = events[-1]["data"]["message"]

    assert message == f"Please enter a pain level between 0 and 10. {PAIN_LEVEL_PROMPT}"
    assert main.SESSION_STORE[session_id]["current_field"] == "pain_level"
    assert "pain_level" not in main.SESSION_STORE[session_id]["collected_data"]


def test_implausible_pain_level_is_rejected_before_estimate(client: TestClient) -> None:
    session_id = "implausible-pain-session"
    _run_flow(client, session_id, EMERGENCY_FLOW[:4])

    events = _post_chat(client, session_id, "24")
    message = events[-1]["data"]["message"]

    assert message == f"Please enter a pain level between 0 and 10. {PAIN_LEVEL_PROMPT}"
    assert main.SESSION_STORE[session_id]["current_field"] == "pain_level"
    assert "pain_level" not in main.SESSION_STORE[session_id]["collected_data"]


def test_invalid_issue_type_enum_reprompts_without_advancing(client: TestClient) -> None:
    session_id = "invalid-enum-session"
    _run_flow(client, session_id, EMERGENCY_FLOW[:3])

    events = _post_chat(client, session_id, "laser")
    message = events[-1]["data"]["message"].lower()

    assert "please choose one of" in message
    assert "toothache, chipped_tooth, swelling, lost_filling" in message
    assert main.SESSION_STORE[session_id]["current_field"] == "issue_type"
    assert "issue_type" not in main.SESSION_STORE[session_id]["collected_data"]


def test_i_like_dogs_is_rejected_as_patient_name(client: TestClient) -> None:
    """Regression for the old conversational-filler location bug class."""
    session_id = "filler-name-session"

    _post_chat(client, session_id, "I want to book a cleaning")
    events = _post_chat(client, session_id, "i like dogs")

    message = events[-1]["data"]["message"]
    assert "patient's full name" in message.lower()
    assert message.endswith(PATIENT_NAME_PROMPT)
    assert main.SESSION_STORE[session_id]["current_field"] == "patient_name"
    assert "patient_name" not in main.SESSION_STORE[session_id]["collected_data"]


def test_dental_question_during_text_field_is_rejected_without_advancing(client: TestClient) -> None:
    session_id = "dental-question-field-session"

    _post_chat(client, session_id, "I want to book a cleaning")
    events = _post_chat(client, session_id, "how much does whitening cost")

    message = events[-1]["data"]["message"]
    assert message == (
        "Please enter the requested detail, not a new appointment question. "
        f"{PATIENT_NAME_PROMPT}"
    )
    assert main.SESSION_STORE[session_id]["current_field"] == "patient_name"
    assert main.SESSION_STORE[session_id]["intake_step"] == "collect"
    assert "patient_name" not in main.SESSION_STORE[session_id]["collected_data"]


def test_invalid_email_is_rejected_without_advancing(client: TestClient) -> None:
    session_id = "invalid-email-session"

    _post_chat(client, session_id, "I want to book a cleaning")
    _post_chat(client, session_id, "Maria Santos")
    events = _post_chat(client, session_id, "not-an-email")

    message = events[-1]["data"]["message"]
    assert "valid email address" in message.lower()
    assert message.endswith(CONTACT_EMAIL_PROMPT)
    assert main.SESSION_STORE[session_id]["current_field"] == "contact_email"
    assert "contact_email" not in main.SESSION_STORE[session_id]["collected_data"]


def test_short_phone_number_is_rejected_without_advancing(client: TestClient) -> None:
    session_id = "short-phone-session"

    _post_chat(client, session_id, "I need to book an emergency visit")
    _post_chat(client, session_id, "Ken Garcia")
    events = _post_chat(client, session_id, "12345")

    message = events[-1]["data"]["message"]
    assert message == (
        f"Please enter a phone number with at least 7 digits. {CONTACT_PHONE_PROMPT}"
    )
    assert main.SESSION_STORE[session_id]["current_field"] == "contact_phone"
    assert "contact_phone" not in main.SESSION_STORE[session_id]["collected_data"]


def test_invalid_text_replies_during_year_field_do_not_leave_intake_flow(client: TestClient) -> None:
    session_id = "invalid-text-year-session"

    _post_chat(client, session_id, "I want to book a cleaning")
    _post_chat(client, session_id, "Maria Santos")
    _post_chat(client, session_id, "maria@example.com")
    first_retry = _post_chat(client, session_id, "checkup")
    second_retry = _post_chat(client, session_id, "yes continue")

    first_message = first_retry[-1]["data"]["message"].lower()
    second_message = second_retry[-1]["data"]["message"].lower()

    assert "please enter a whole number" in first_message
    assert "what year was your last dental visit?" in first_message
    assert "please enter a whole number" in second_message
    assert "what year was your last dental visit?" in second_message
    state = main.SESSION_STORE[session_id]
    assert state["intake_step"] == "collect"
    assert state["current_field"] == "last_visit_year"
    assert state["service_type"] == "cleaning"
    assert state["collected_data"] == {
        "patient_name": "Maria Santos",
        "contact_email": "maria@example.com",
    }


# ── Confirm step: accept / adjust / restart / switch ──────────────────────────

def test_adjust_reopens_collection_from_first_field(client: TestClient) -> None:
    session_id = "adjust-session"
    _run_flow(client, session_id, CLEANING_FLOW)

    events = _post_chat(client, session_id, "adjust")
    message = events[-1]["data"]["message"]

    assert message == PATIENT_NAME_PROMPT
    assert main.SESSION_STORE[session_id]["visit_estimate"] is None
    assert main.SESSION_STORE[session_id]["current_field"] == "patient_name"
    assert main.SESSION_STORE[session_id]["collected_data"] == {}


def test_restart_during_confirm_resets_service_selection(client: TestClient) -> None:
    session_id = "restart-confirm-session"
    _run_flow(client, session_id, CLEANING_FLOW)

    events = _post_chat(client, session_id, "restart")
    payload = events[-1]["data"]

    assert "which type of visit would you like to set up" in payload["message"].lower()
    assert payload["session"]["intake_step"] == "identify"
    assert payload["session"]["service_type"] is None
    assert payload["session"]["has_visit_estimate"] is False


def test_switching_service_mid_flow_resets_to_new_service(client: TestClient) -> None:
    session_id = "switch-service-session"

    _post_chat(client, session_id, "I want to book a cleaning")
    _post_chat(client, session_id, "Maria Santos")
    events = _post_chat(client, session_id, "Actually, I need to book an emergency visit instead")

    assert events[-1]["data"]["message"] == PATIENT_NAME_PROMPT
    state = main.SESSION_STORE[session_id]
    assert state["service_type"] == "emergency"
    assert state["current_field"] == "patient_name"
    assert state["collected_data"] == {}


def test_session_store_mirror_exposes_intake_keys(client: TestClient) -> None:
    session_id = "mirror-keys-session"

    _post_chat(client, session_id, "I want to book a cleaning")
    state = main.SESSION_STORE[session_id]

    for key in ("mode", "intake_step", "current_field", "service_type", "collected_data", "visit_estimate"):
        assert key in state
    assert state["mode"] == "transactional"
    assert state["intake_step"] == "collect"
    assert state["service_type"] == "cleaning"


# ── Deterministic re-architecture: durable memory, RAG history, pure routing ──

def test_state_persists_across_graph_rebuild(client: TestClient) -> None:
    """State lives in the checkpointer, not the in-process graph object.

    Rebuilding the compiled graph (a stand-in for a process restart) while
    reusing the same checkpointer must preserve the conversation state.
    """
    import graph

    _post_chat(client, "persist-session", "I want to book a cleaning")
    _post_chat(client, "persist-session", "Maria Santos")

    graph.COMPILED_GRAPH = graph._build_graph().compile(checkpointer=graph._checkpointer)

    state = graph.get_session_state("persist-session")
    assert state is not None
    assert state["collected_data"]["patient_name"] == "Maria Santos"
    assert state["current_field"] == "contact_email"


def test_rag_includes_prior_conversation_as_history(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A follow-up question sends prior turns to the LLM as history."""
    import nodes.rag as rag

    captured: dict[str, Any] = {}

    class _FakeClient:
        model = "fake-model"

        def chat_text(self, *, system_prompt, user_prompt, history=None, on_token=None, **_):
            captured["history"] = list(history or [])
            return "Here is the canned answer."

    monkeypatch.setattr(rag, "_build_client_or_none", lambda: _FakeClient())

    _post_chat(client, "history-session", "Tell me about teeth whitening")
    _post_chat(client, "history-session", "Is it safe for sensitive teeth?")

    history = captured.get("history")
    assert history is not None, "RAG did not pass conversation history to the LLM"
    user_turns = [m["content"].lower() for m in history if m["role"] == "user"]
    assistant_turns = [m["content"] for m in history if m["role"] == "assistant"]
    assert any("teeth whitening" in turn for turn in user_turns)
    assert "Here is the canned answer." in assistant_turns


def test_routing_is_a_pure_function_without_any_llm() -> None:
    """decide() routes purely from (state, message) — no LLM, no randomness."""
    from nodes.router import decide

    state = {
        "mode": "transactional",
        "intake_step": "collect",
        "current_field": "last_visit_year",
        "service_type": "cleaning",
    }
    assert decide(state, "2024") == "collect"
    assert decide(state, "what does a routine cleaning include?") == "answer_then_resume"
    assert decide(state, "restart") == "confirm"
    assert decide(dict(state), "2024") == decide(dict(state), "2024")


# ── Front-desk integrations on accept ─────────────────────────────────────────

class _FakeHTTPResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *args: Any) -> bool:
        return False


class _FakeUrlopen:
    """Records every request; optionally fails for URLs matching a substring."""

    def __init__(self, error_url_substring: str | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.error_url_substring = error_url_substring

    def __call__(self, request: urllib.request.Request, timeout: float | None = None) -> _FakeHTTPResponse:
        url = request.full_url
        self.calls.append(
            {
                "url": url,
                "payload": json.loads(request.data.decode("utf-8")),
                "headers": {name.lower(): value for name, value in request.header_items()},
            }
        )
        if self.error_url_substring and self.error_url_substring in url:
            raise urllib.error.HTTPError(url, 500, "Server Error", None, None)
        if "api.airtable.com" in url:
            return _FakeHTTPResponse(json.dumps({"records": [{"id": "recTEST123"}]}).encode("utf-8"))
        return _FakeHTTPResponse(b"{}")

    def call_for(self, url_substring: str) -> dict[str, Any]:
        for call in self.calls:
            if url_substring in call["url"]:
                return call
        raise AssertionError(f"No request captured for {url_substring!r}")


def _configure_integrations(monkeypatch: pytest.MonkeyPatch, fake_urlopen: _FakeUrlopen) -> None:
    import services.airtable as airtable
    import services.calcom as calcom
    import services.resend_email as resend_email

    monkeypatch.setenv("AIRTABLE_API_KEY", "test-airtable-key")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "appTESTBASE")
    monkeypatch.setenv("CALCOM_API_KEY", "test-cal-key")
    monkeypatch.setenv("CALCOM_EVENT_TYPE_ID", "12345")
    monkeypatch.setenv("RESEND_API_KEY", "test-resend-key")

    # The three clients share the stdlib urllib.request module; patching it at
    # each client module keeps every outbound POST in-process.
    monkeypatch.setattr(airtable.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(calcom.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(resend_email.urllib.request, "urlopen", fake_urlopen)


def test_accept_with_configured_integrations_posts_real_payloads(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_urlopen = _FakeUrlopen()
    _configure_integrations(monkeypatch, fake_urlopen)

    session_id = "live-integrations-session"
    _run_flow(client, session_id, CLEANING_FLOW)
    events = _post_chat(client, session_id, "accept")

    message = events[-1]["data"]["message"]
    assert "- Airtable CRM: New lead saved to the clinic CRM (record recTEST123)." in message
    assert "- Cal.com booking: Appointment requested for" in message
    assert "- Email confirmation: Confirmation email sent to maria@example.com." in message

    assert len(fake_urlopen.calls) == 3

    airtable_call = fake_urlopen.call_for("api.airtable.com")
    assert airtable_call["url"] == "https://api.airtable.com/v0/appTESTBASE/Leads"
    assert airtable_call["headers"]["authorization"] == "Bearer test-airtable-key"
    fields = airtable_call["payload"]["records"][0]["fields"]
    assert fields["Name"] == "Maria Santos"
    assert fields["Contact"] == "maria@example.com"
    assert fields["Service"] == "cleaning"
    assert fields["Status"] == "New"
    assert fields["Estimate Low"] < fields["Estimate High"]
    assert json.loads(fields["Details"])["last_visit_year"] == 2024

    calcom_call = fake_urlopen.call_for("api.cal.com")
    assert calcom_call["url"] == "https://api.cal.com/v2/bookings"
    assert calcom_call["headers"]["authorization"] == "Bearer test-cal-key"
    assert calcom_call["headers"]["cal-api-version"] == "2024-08-13"
    assert calcom_call["payload"]["eventTypeId"] == 12345
    assert calcom_call["payload"]["attendee"]["name"] == "Maria Santos"
    assert calcom_call["payload"]["attendee"]["email"] == "maria@example.com"
    assert calcom_call["payload"]["metadata"] == {"service_type": "cleaning"}
    # Deterministic morning slot: next business day at 09:00 UTC.
    assert calcom_call["payload"]["start"].endswith("Z")
    assert "T09:00:00" in calcom_call["payload"]["start"]

    resend_call = fake_urlopen.call_for("api.resend.com")
    assert resend_call["url"] == "https://api.resend.com/emails"
    assert resend_call["headers"]["authorization"] == "Bearer test-resend-key"
    assert resend_call["payload"]["to"] == ["maria@example.com"]
    assert resend_call["payload"]["from"] == "Ivory <onboarding@resend.dev>"
    assert resend_call["payload"]["subject"] == "Your Ivory Dental Studio visit request"
    assert "cleaning visit request" in resend_call["payload"]["text"]


def test_integration_http_error_yields_error_line_but_accept_succeeds(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_urlopen = _FakeUrlopen(error_url_substring="api.airtable.com")
    _configure_integrations(monkeypatch, fake_urlopen)

    session_id = "integration-error-session"
    _run_flow(client, session_id, CLEANING_FLOW)
    events = _post_chat(client, session_id, "accept")

    assert events[-1]["event"] == "message_complete"
    message = events[-1]["data"]["message"]
    assert "Confirmed." in message
    assert "- Airtable CRM: Airtable lead could not be saved (HTTP 500)." in message
    # The failing integration never blocks the others or the accept turn.
    assert "- Cal.com booking: Appointment requested for" in message
    assert "- Email confirmation: Confirmation email sent to maria@example.com." in message
    assert events[-1]["data"]["session"]["mode"] == "conversational"


def test_emergency_accept_skips_email_and_reports_phone_contact(client: TestClient) -> None:
    session_id = "emergency-accept-session"
    _run_flow(client, session_id, EMERGENCY_FLOW)

    events = _post_chat(client, session_id, "accept")
    message = events[-1]["data"]["message"]

    assert "Front desk actions:" in message
    assert "- Airtable CRM: Airtable (demo mode): lead captured locally" in message
    assert "- Cal.com booking: Cal.com (demo mode): booking request recorded locally" in message
    # Emergency collects a phone, not an email — the email step is skipped, not errored.
    assert (
        "- Email confirmation: No email on file for this visit (phone contact only) — "
        "the front desk will call instead." in message
    )
    assert "Resend (demo mode)" not in message


# ---------------------------------------------------------------------------
# Adversarial-review regressions (post-conversion hardening)
# ---------------------------------------------------------------------------


def test_midflow_question_with_booking_word_answers_then_resumes(client: TestClient) -> None:
    """A '?' question mentioning 'appointment' must never hijack the intake."""
    session_id = "review-hijack-session"
    _run_flow(client, session_id, CLEANING_FLOW[:3])  # asking last_visit_year

    events = _post_chat(client, session_id, "How much does a whitening appointment usually cost?")
    message = events[-1]["data"]["message"]

    assert "What year was your last dental visit? (e.g. 2024)" in message
    session = main.SESSION_STORE[session_id]
    assert session["service_type"] == "cleaning"
    assert session["collected_data"]["patient_name"] == "Maria Santos"
    assert session["collected_data"]["contact_email"] == "maria@example.com"


def test_domain_word_surnames_are_valid_patient_names(client: TestClient) -> None:
    """'Price'/'Costa' are common surnames, not appointment questions."""
    for index, name in enumerate(["Sarah Price", "George Costa"]):
        session_id = f"review-surname-{index}"
        _post_chat(client, session_id, "I'd like to book a cleaning")
        _post_chat(client, session_id, name)
        assert main.SESSION_STORE[session_id]["collected_data"]["patient_name"] == name

    # Pure domain-word or question-shaped answers are still rejected.
    session_id = "review-surname-reject"
    _post_chat(client, session_id, "I'd like to book a cleaning")
    events = _post_chat(client, session_id, "do you offer implants")
    assert "patient_name" not in main.SESSION_STORE[session_id]["collected_data"]
    assert "What's the patient's full name?" in events[-1]["data"]["message"]


def test_negated_confirm_reply_never_accepts(client: TestClient) -> None:
    """'no, this is not ok' must not fire the front-desk integrations."""
    session_id = "review-negation-session"
    _run_flow(client, session_id, CLEANING_FLOW)

    for rejection in ("no, this is not ok", "yesterday", "not good"):
        events = _post_chat(client, session_id, rejection)
        message = events[-1]["data"]["message"]
        assert "Front desk actions:" not in message
        assert "accept, adjust, or restart" in message
        assert main.SESSION_STORE[session_id]["visit_estimate"] is not None

    events = _post_chat(client, session_id, "accept")
    assert "Front desk actions:" in events[-1]["data"]["message"]


def test_name_containing_book_substring_is_collected(client: TestClient) -> None:
    """'Booker Smith' must be stored, not rerouted as a booking request."""
    session_id = "review-booker-session"
    _post_chat(client, session_id, "I'd like to book a cleaning")
    _post_chat(client, session_id, "Booker Smith")
    assert main.SESSION_STORE[session_id]["collected_data"]["patient_name"] == "Booker Smith"


def test_email_local_part_never_fills_other_fields(client: TestClient) -> None:
    """Digits or day-part words inside the email must not be absorbed."""
    session_id = "review-email-absorb-session"
    _post_chat(client, session_id, "I'd like to book a cleaning")
    _post_chat(client, session_id, "Maria Santos")
    events = _post_chat(client, session_id, "maria.1990@example.com")

    collected = main.SESSION_STORE[session_id]["collected_data"]
    assert collected["contact_email"] == "maria.1990@example.com"
    assert "last_visit_year" not in collected
    assert "What year was your last dental visit? (e.g. 2024)" in events[-1]["data"]["message"]


def test_accept_clears_intake_and_next_intake_starts_fresh(client: TestClient) -> None:
    """An accepted visit must not leak answers or estimate into the next intake."""
    session_id = "review-fresh-intake-session"
    _run_flow(client, session_id, CLEANING_FLOW)
    events = _post_chat(client, session_id, "accept")
    session_payload = events[-1]["data"]["session"]
    assert session_payload["has_visit_estimate"] is False

    events = _post_chat(client, session_id, "book an emergency visit")
    session = main.SESSION_STORE[session_id]
    assert session["service_type"] == "emergency"
    assert session["collected_data"] == {}
    assert "What's the patient's full name?" in events[-1]["data"]["message"]


def test_compact_input_fills_emergency_and_cosmetic(client: TestClient) -> None:
    """The comma-separated multi-field reply works for every service."""
    session_id = "review-compact-emergency"
    _post_chat(client, session_id, "I need to book an emergency visit")
    events = _post_chat(client, session_id, "Ken Garcia, 555-201-7788, toothache, 7, insured")
    payload = events[-1]["data"]
    assert payload["visit_estimate"] is not None
    assert payload["visit_estimate"]["service_type"] == "emergency"

    session_id = "review-compact-cosmetic"
    _post_chat(client, session_id, "I want to book a cosmetic consultation")
    events = _post_chat(client, session_id, "Maria Santos, maria@example.com, whitening, standard, asap")
    payload = events[-1]["data"]
    assert payload["visit_estimate"] is not None
    assert payload["visit_estimate"]["service_type"] == "cosmetic"


def test_phone_number_extracted_from_sentence(client: TestClient) -> None:
    """The stored phone is the number itself, not the sentence around it."""
    session_id = "review-phone-session"
    _post_chat(client, session_id, "I need to book an emergency visit")
    _post_chat(client, session_id, "Ken Garcia")
    _post_chat(client, session_id, "you can reach me at 555-201-7788 any time")
    assert main.SESSION_STORE[session_id]["collected_data"]["contact_phone"] == "555-201-7788"


def test_question_at_confirm_step_never_wipes_estimate(client: TestClient) -> None:
    """A booking-word question on a finished estimate is answered, not a switch."""
    session_id = "review-confirm-question"
    _run_flow(client, session_id, CLEANING_FLOW)
    assert main.SESSION_STORE[session_id]["intake_step"] == "confirm"

    events = _post_chat(client, session_id, "How much does a whitening appointment cost?")
    session = main.SESSION_STORE[session_id]
    assert session["visit_estimate"] is not None
    assert session["service_type"] == "cleaning"
    assert session["intake_step"] == "confirm"


def test_not_insured_is_stored_as_self_pay(client: TestClient) -> None:
    """'I'm not insured' must not be read as insured (substring trap)."""
    session_id = "review-not-insured"
    _run_flow(client, session_id, CLEANING_FLOW[:4])  # through last_visit_year
    _post_chat(client, session_id, "I'm not insured")
    assert main.SESSION_STORE[session_id]["collected_data"]["insurance_status"] == "self_pay"


def test_plain_name_does_not_absorb_other_fields(client: TestClient) -> None:
    """A two-word name whose tokens look like enum values fills only the name."""
    for name in ("Cash Morgan", "Morning Star"):
        session_id = f"review-name-absorb-{name.split()[0]}"
        _post_chat(client, session_id, "I'd like to book a cleaning")
        _post_chat(client, session_id, name)
        collected = main.SESSION_STORE[session_id]["collected_data"]
        assert collected == {"patient_name": name}


def test_negated_confirm_reply_does_not_adjust(client: TestClient) -> None:
    """'No, don't change anything' contains 'change' but must not fire adjust."""
    session_id = "review-negated-adjust"
    _run_flow(client, session_id, CLEANING_FLOW)
    events = _post_chat(client, session_id, "No, don't change anything")
    session = main.SESSION_STORE[session_id]
    assert session["visit_estimate"] is not None
    assert session["collected_data"] != {}
    assert "accept, adjust, or restart" in events[-1]["data"]["message"]

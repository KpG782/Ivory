from __future__ import annotations

import sys
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

# _parse_sse_body, _post_chat, and the `client` fixture are defined in conftest.py
# and are automatically available to all tests in this directory.
from conftest import _parse_sse_body, _post_chat


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


def test_chat_question_streams_sse_events(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={"session_id": "question-session", "message": "What does comprehensive cover?"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse_body(response.text)

    assert events[0]["event"] == "token"
    assert events[-1]["event"] == "message_complete"
    assert "comprehensive coverage" in events[-1]["data"]["message"].lower()
    assert events[-1]["data"]["session"]["mode"] == "conversational"
    assert events[-1]["data"]["session"]["intake_step"] == "identify"


def test_rag_fallback_returns_clean_direct_answer_without_llm(client: TestClient) -> None:
    events = _post_chat(client, "fallback-rag-session", "What does comprehensive coverage include?")

    message = events[-1]["data"]["message"].lower()
    assert "comprehensive coverage generally includes non-collision damage" in message
    assert "based on the knowledge base" not in message


def test_full_dental_flow_accept_reaches_booked(client: TestClient) -> None:
    """Full dental booking flow: cleaning → 5 fields → validate → confirm → accept → booked."""
    # Task 7 extends this with booking_result assertions
    session_id = "dental-booking-session"
    prompts = [
        "I'd like to book a cleaning",
        "Maria Santos",
        "9175550144",
        "maria@example.com",
        "new",
        "Wednesday 2:30 PM",
    ]

    final_events: list[dict[str, Any]] = []
    for message in prompts:
        final_events = _post_chat(client, session_id, message)

    payload = final_events[-1]["data"]
    assert payload["session"]["intake_step"] == "confirm"
    assert payload["session"]["service_type"] == "cleaning"
    assert "Maria Santos" in payload["message"]
    assert "cleaning" in payload["message"].lower()

    # Accept → booked
    accept_events = _post_chat(client, session_id, "accept")
    accept_payload = accept_events[-1]["data"]
    assert accept_payload["session"]["intake_step"] == "booked"
    assert accept_payload["session"]["mode"] == "conversational"
    assert "Maria Santos" in accept_payload["message"]


def test_adjust_reopens_collection_from_first_field(client: TestClient) -> None:
    """After completing all fields + validating, 'adjust' restarts collection."""
    session_id = "adjust-session"
    prompts = [
        "I'd like to book a cleaning",
        "Maria Santos",
        "9175550144",
        "maria@example.com",
        "new",
        "Wednesday 2:30 PM",
    ]
    for message in prompts:
        _post_chat(client, session_id, message)

    events = _post_chat(client, session_id, "adjust")
    message = events[-1]["data"]["message"]

    assert "may i have your full name" in message.lower()
    assert main.SESSION_STORE[session_id]["current_field"] == "patient_name"
    assert main.SESSION_STORE[session_id]["collected_data"] == {}


def test_explicit_quote_request_starts_collection(client: TestClient) -> None:
    events = _post_chat(client, "quote-start-session", "I'd like to book an appointment")
    payload = events[-1]["data"]

    # P2 "book" → start_intake → identify_service → dental service prompt
    # (no dental service keyword → stays at identify, prompts which service)
    assert payload["session"]["mode"] == "transactional"
    assert payload["session"]["intake_step"] == "identify"
    assert payload["session"]["service_type"] is None


def test_numeric_field_reply_stays_in_quote_flow(client: TestClient) -> None:
    """A phone number is stored as the phone field and advances to email."""
    session_id = "numeric-field-session"

    _post_chat(client, session_id, "I'd like to book a cleaning")
    _post_chat(client, session_id, "Maria Santos")
    events = _post_chat(client, session_id, "(917) 555-0144")

    payload = events[-1]["data"]
    assert "and your email for the confirmation" in payload["message"].lower()
    assert main.SESSION_STORE[session_id]["collected_data"]["phone"] == "9175550144"


def test_invalid_numeric_input_reprompts_without_advancing(client: TestClient) -> None:
    """An invalid phone number is rejected; current_field stays 'phone'."""
    session_id = "invalid-numeric-session"

    _post_chat(client, session_id, "I'd like to book a cleaning")
    _post_chat(client, session_id, "Maria Santos")
    events = _post_chat(client, session_id, "abc")

    message = events[-1]["data"]["message"].lower()
    assert "phone number" in message
    assert "area code" in message
    assert main.SESSION_STORE[session_id]["current_field"] == "phone"
    assert "phone" not in main.SESSION_STORE[session_id]["collected_data"]


def test_invalid_enum_input_reprompts_without_advancing(client: TestClient) -> None:
    """An invalid patient_status is rejected; allowed values are mentioned."""
    session_id = "invalid-enum-session"
    prompts = [
        "I'd like to book a cleaning",
        "Maria Santos",
        "9175550144",
        "maria@example.com",
    ]
    for message in prompts:
        _post_chat(client, session_id, message)

    events = _post_chat(client, session_id, "platinum")
    message = events[-1]["data"]["message"].lower()

    assert "please choose one of" in message
    assert "new" in message
    assert "returning" in message
    assert main.SESSION_STORE[session_id]["current_field"] == "patient_status"


def test_mid_flow_question_preserves_quote_progress(client: TestClient) -> None:
    """A '?' question mid-intake is answered, then the same field is re-asked."""
    session_id = "interrupt-session"

    start_events = _post_chat(client, session_id, "I'd like to book a cleaning")
    assert "may i have your full name" in start_events[-1]["data"]["message"].lower()

    question_events = _post_chat(client, session_id, "do you take walk-ins?")
    question_message = question_events[-1]["data"]["message"]

    # RAG answers, then re-asks the paused field (patient_name)
    assert "comprehensive coverage" in question_message.lower()
    assert "may i have your full name" in question_message.lower()
    assert main.SESSION_STORE[session_id]["current_field"] == "patient_name"
    assert question_events[-1]["data"]["session"]["intake_step"] == "collect"

    resume_events = _post_chat(client, session_id, "Maria Santos")
    assert "what's the best phone number" in resume_events[-1]["data"]["message"].lower()
    assert main.SESSION_STORE[session_id]["collected_data"]["patient_name"] == "Maria Santos"


def test_mid_quote_question_answers_then_resumes_same_field(client: TestClient) -> None:
    """A '?' question while collecting re-asks the same paused field."""
    session_id = "mid-quote-question-session"

    _post_chat(client, session_id, "I'd like to book a cleaning")

    events = _post_chat(client, session_id, "What does comprehensive coverage include?")
    payload = events[-1]["data"]

    assert "comprehensive coverage" in payload["message"].lower()
    assert "may i have your full name" in payload["message"].lower()
    assert payload["session"]["mode"] == "transactional"
    assert payload["session"]["intake_step"] == "collect"


def test_switching_product_mid_flow_resets_to_new_product(client: TestClient) -> None:
    """Switching service mid-flow resets collected_data and restarts collection."""
    session_id = "switch-product-session"

    _post_chat(client, session_id, "I'd like to book a cleaning")
    _post_chat(client, session_id, "Maria Santos")
    events = _post_chat(client, session_id, "actually book a whitening instead")

    payload = events[-1]["data"]
    assert "may i have your full name" in payload["message"].lower()
    state = main.SESSION_STORE[session_id]
    assert state["service_type"] == "whitening"
    assert state["current_field"] == "patient_name"
    assert state["collected_data"] == {}


def test_quote_flow_starts_in_identify_mode_instead_of_rag(client: TestClient) -> None:
    session_id = "start-quote-session"

    events = _post_chat(client, session_id, "I'd like to book an appointment")
    payload = events[-1]["data"]

    # P2 "book" → start_intake → identify_service → dental service prompt
    assert "which service would you like to book" in payload["message"].lower()
    assert payload["session"]["mode"] == "transactional"
    assert payload["session"]["intake_step"] == "identify"
    assert payload["session"]["service_type"] is None


def test_restart_during_confirm_resets_product_selection(client: TestClient) -> None:
    session_id = "restart-confirm-session"

    # Start an intake — P2 "book" → start_intake → identify_service → dental prompt
    _post_chat(client, session_id, "I'd like to book an appointment")

    events = _post_chat(client, session_id, "restart")
    payload = events[-1]["data"]

    # restart triggers confirm node → _reset_intake_state → dental restart prompt
    assert payload["session"]["intake_step"] == "identify"
    assert payload["session"]["service_type"] is None
    assert payload["session"]["has_booking_result"] is False


# ── Deterministic re-architecture: durable memory, RAG history, pure routing ──

def test_state_persists_across_graph_rebuild(client: TestClient) -> None:
    """State lives in the checkpointer, not the in-process graph object.

    Rebuilding the compiled graph (a stand-in for a process restart) while
    reusing the same checkpointer must preserve the conversation state.
    """
    import graph

    _post_chat(client, "persist-session", "I'd like to book an appointment")

    graph.COMPILED_GRAPH = graph._build_graph().compile(checkpointer=graph._checkpointer)

    state = graph.get_session_state("persist-session")
    assert state is not None
    # After "I'd like to book an appointment" → start_intake → identify_service, mode is transactional
    assert state["mode"] == "transactional"
    assert state["intake_step"] == "identify"


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

    _post_chat(client, "history-session", "Tell me about life insurance")
    _post_chat(client, "history-session", "What is the maximum benefit?")

    history = captured.get("history")
    assert history is not None, "RAG did not pass conversation history to the LLM"
    user_turns = [m["content"].lower() for m in history if m["role"] == "user"]
    assistant_turns = [m["content"] for m in history if m["role"] == "assistant"]
    assert any("life insurance" in turn for turn in user_turns)
    assert "Here is the canned answer." in assistant_turns


def test_routing_is_a_pure_function_without_any_llm() -> None:
    """decide() routes purely from (state, message) — no LLM, no randomness."""
    from nodes.router import decide

    state = {
        "mode": "transactional",
        "intake_step": "collect",
        "current_field": "phone",
        "service_type": "cleaning",
    }
    assert decide(state, "09171234567") == "collect"
    assert decide(state, "do you take walk-ins?") == "answer_then_resume"
    assert decide(state, "restart") == "confirm"
    assert decide(dict(state), "09171234567") == decide(dict(state), "09171234567")

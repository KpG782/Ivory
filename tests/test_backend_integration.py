from __future__ import annotations

import json
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


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import nodes.rag as rag

    # Disable rate limiting so the test suite does not hit per-IP limits.
    # _is_rate_limit_disabled() reads this env var at request time, so
    # monkeypatch.setenv is effective even though main.py is already imported.
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

    main.SESSION_STORE.clear()

    # Routing is deterministic (no LLM), so there is no classifier to stub. We
    # only stub the RAG LLM client + retrieval so tests are hermetic/offline.
    monkeypatch.setattr(rag, "_build_client_or_none", lambda: None)
    monkeypatch.setattr(
        rag,
        "search_knowledge_base",
        lambda *args, **kwargs: [
            RetrievedChunk(
                id="kb-1",
                score=0.99,
                source="02_auto_insurance.md",
                title="Auto Insurance",
                content=(
                    "Comprehensive coverage typically includes non-collision losses such as "
                    "theft, vandalism, fire, weather damage, and falling objects."
                ),
                metadata={"source": "02_auto_insurance.md", "title": "Auto Insurance"},
            )
        ],
    )

    with TestClient(main.app) as test_client:
        yield test_client

    main.SESSION_STORE.clear()


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


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_auto_quote_flow_returns_quote_result(client: TestClient) -> None:
    session_id = "quote-session"
    prompts = [
        "I want a quote for auto insurance",
        "2019",
        "Toyota",
        "Camry",
        "35",
        "0",
        "standard",
    ]

    final_events: list[dict[str, Any]] = []
    for message in prompts:
        response = client.post("/chat", json={"session_id": session_id, "message": message})
        assert response.status_code == 200
        final_events = _parse_sse_body(response.text)

    assert final_events[-1]["event"] == "message_complete"
    payload = final_events[-1]["data"]
    assert payload["booking_result"]["product_type"] == "auto"
    assert payload["booking_result"]["coverage_level"] == "standard"
    assert payload["booking_result"]["premium"] > 0
    assert "estimated auto premium" in payload["message"].lower()
    assert payload["session"]["mode"] == "transactional"
    assert payload["session"]["intake_step"] == "confirm"
    assert payload["session"]["has_booking_result"] is True


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_home_quote_flow_returns_quote_result(client: TestClient) -> None:
    session_id = "home-quote-session"
    prompts = [
        "I want a quote for home insurance",
        "house",
        "Austin",
        "350000",
        "2005",
        "comprehensive",
    ]

    final_events: list[dict[str, Any]] = []
    for message in prompts:
        final_events = _post_chat(client, session_id, message)

    payload = final_events[-1]["data"]
    assert payload["booking_result"]["product_type"] == "home"
    assert payload["booking_result"]["coverage_level"] == "comprehensive"
    assert payload["booking_result"]["premium"] > 0
    assert payload["session"]["intake_step"] == "confirm"


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_life_quote_flow_returns_quote_result(client: TestClient) -> None:
    session_id = "life-quote-session"
    prompts = [
        "I want a quote for life insurance",
        "42",
        "good",
        "no",
        "500000",
        "20",
        "standard",
    ]

    final_events: list[dict[str, Any]] = []
    for message in prompts:
        final_events = _post_chat(client, session_id, message)

    payload = final_events[-1]["data"]
    assert payload["booking_result"]["product_type"] == "life"
    assert payload["booking_result"]["coverage_level"] == "standard"
    assert payload["booking_result"]["premium"] > 0
    assert payload["session"]["intake_step"] == "confirm"


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_mid_flow_question_preserves_quote_progress(client: TestClient) -> None:
    session_id = "interrupt-session"

    start_response = client.post(
        "/chat",
        json={"session_id": session_id, "message": "I want a quote for auto insurance"},
    )
    start_events = _parse_sse_body(start_response.text)
    assert start_events[-1]["data"]["message"] == "What year is the vehicle? (e.g. 2019)"

    question_response = client.post(
        "/chat",
        json={"session_id": session_id, "message": "What does comprehensive cover?"},
    )
    question_events = _parse_sse_body(question_response.text)
    question_message = question_events[-1]["data"]["message"]

    assert "comprehensive coverage" in question_message.lower()
    assert "what year is the vehicle?" in question_message.lower()
    assert main.SESSION_STORE[session_id]["current_field"] == "vehicle_year"
    assert question_events[-1]["data"]["session"]["intake_step"] == "collect"

    resume_response = client.post(
        "/chat",
        json={"session_id": session_id, "message": "2019"},
    )
    resume_events = _parse_sse_body(resume_response.text)

    assert resume_events[-1]["data"]["message"] == "What is the vehicle make? (e.g. Toyota)"
    assert main.SESSION_STORE[session_id]["collected_data"]["vehicle_year"] == 2019


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_numeric_field_reply_stays_in_quote_flow(client: TestClient) -> None:
    """A bare value like "2019" is always stored as the field, never re-routed."""
    session_id = "numeric-field-session"

    _post_chat(client, session_id, "I want a quote for auto insurance")
    events = _post_chat(client, session_id, "2019")

    assert events[-1]["data"]["message"] == "What is the vehicle make? (e.g. Toyota)"
    assert main.SESSION_STORE[session_id]["collected_data"]["vehicle_year"] == 2019


def test_explicit_quote_request_starts_collection(client: TestClient) -> None:
    events = _post_chat(client, "quote-start-session", "I'd like to book an appointment")
    payload = events[-1]["data"]

    # P2 "book" → start_intake → identify_service → dental service prompt
    # (no dental service keyword → stays at identify, prompts which service)
    assert payload["session"]["mode"] == "transactional"
    assert payload["session"]["intake_step"] == "identify"
    assert payload["session"]["service_type"] is None


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_comma_separated_auto_details_fill_multiple_fields(client: TestClient) -> None:
    session_id = "comma-separated-auto-session"

    _post_chat(client, session_id, "I want a quote for auto insurance")
    _post_chat(client, session_id, "2019")
    events = _post_chat(client, session_id, "Toyota, Camry, 35, 0, standard")

    payload = events[-1]["data"]
    assert "estimated auto premium" in payload["message"].lower()
    assert payload["booking_result"]["product_type"] == "auto"
    assert payload["booking_result"]["coverage_level"] == "standard"

    state = main.SESSION_STORE[session_id]
    assert state["collected_data"]["vehicle_make"] == "Toyota"
    assert state["collected_data"]["vehicle_model"] == "Camry"
    assert state["collected_data"]["driver_age"] == 35
    assert state["collected_data"]["accidents_last_5yr"] == 0


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_mid_quote_question_answers_then_resumes_same_field(client: TestClient) -> None:
    session_id = "mid-quote-question-session"

    _post_chat(client, session_id, "I want a quote for auto insurance")

    events = _post_chat(client, session_id, "What does comprehensive coverage include?")
    payload = events[-1]["data"]

    assert "comprehensive coverage" in payload["message"].lower()
    assert "what year is the vehicle?" in payload["message"].lower()
    assert payload["session"]["mode"] == "transactional"
    assert payload["session"]["intake_step"] == "collect"


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_invalid_numeric_input_reprompts_without_advancing(client: TestClient) -> None:
    session_id = "invalid-numeric-session"

    _post_chat(client, session_id, "I want a quote for auto insurance")
    events = _post_chat(client, session_id, "abc")

    message = events[-1]["data"]["message"].lower()
    assert "whole number" in message
    assert "what year is the vehicle?" in message
    assert main.SESSION_STORE[session_id]["current_field"] == "vehicle_year"
    assert "vehicle_year" not in main.SESSION_STORE[session_id]["collected_data"]


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_future_vehicle_year_is_rejected_immediately(client: TestClient) -> None:
    session_id = "future-year-session"

    _post_chat(client, session_id, "I want a quote for auto insurance")
    events = _post_chat(client, session_id, "2035")

    message = events[-1]["data"]["message"]
    assert "vehicle year must be between 1901" in message.lower()
    assert main.SESSION_STORE[session_id]["intake_step"] == "collect"
    assert main.SESSION_STORE[session_id]["current_field"] == "vehicle_year"
    assert "vehicle_year" not in main.SESSION_STORE[session_id]["collected_data"]


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_invalid_enum_input_reprompts_without_advancing(client: TestClient) -> None:
    session_id = "invalid-enum-session"
    prompts = [
        "I want a quote for home insurance",
        "house",
        "Austin",
        "350000",
        "2005",
    ]
    for message in prompts:
        _post_chat(client, session_id, message)

    events = _post_chat(client, session_id, "premium-plus")
    message = events[-1]["data"]["message"].lower()

    assert "please choose one of" in message
    assert "basic, standard, or comprehensive" in message
    assert main.SESSION_STORE[session_id]["current_field"] == "coverage_level"


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_negative_accident_count_is_rejected_before_quote_generation(client: TestClient) -> None:
    session_id = "negative-accidents-session"
    prompts = [
        "I want a quote for auto insurance",
        "2019",
        "Toyota",
        "Camry",
        "35",
    ]
    for message in prompts:
        _post_chat(client, session_id, message)

    events = _post_chat(client, session_id, "-1")
    message = events[-1]["data"]["message"].lower()

    assert "realistic accident count between 0 and 10" in message
    assert main.SESSION_STORE[session_id]["current_field"] == "accidents_last_5yr"
    assert "accidents_last_5yr" not in main.SESSION_STORE[session_id]["collected_data"]


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_off_topic_text_for_string_field_is_rejected(client: TestClient) -> None:
    session_id = "off-topic-session"

    _post_chat(client, session_id, "I want a quote for home insurance")
    _post_chat(client, session_id, "house")
    events = _post_chat(client, session_id, "i like dogs")

    message = events[-1]["data"]["message"].lower()
    assert "city or location" in message or "real city or location" in message
    assert main.SESSION_STORE[session_id]["current_field"] == "location"
    assert "location" not in main.SESSION_STORE[session_id]["collected_data"]


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_policy_question_in_string_field_is_rejected_without_advancing(client: TestClient) -> None:
    session_id = "policy-question-string-session"

    _post_chat(client, session_id, "I want a quote for home insurance")
    _post_chat(client, session_id, "house")
    events = _post_chat(client, session_id, "what insurance products do you offer")

    message = events[-1]["data"]["message"].lower()
    assert "requested detail" in message or "policy question" in message
    assert main.SESSION_STORE[session_id]["current_field"] == "location"
    assert "location" not in main.SESSION_STORE[session_id]["collected_data"]


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_zero_property_value_is_rejected_immediately(client: TestClient) -> None:
    session_id = "zero-property-value-session"
    prompts = [
        "I want a quote for home insurance",
        "house",
        "Austin",
    ]
    for message in prompts:
        _post_chat(client, session_id, message)

    events = _post_chat(client, session_id, "0")
    message = events[-1]["data"]["message"].lower()

    assert "more realistic property value" in message
    assert main.SESSION_STORE[session_id]["current_field"] == "estimated_value"
    assert "estimated_value" not in main.SESSION_STORE[session_id]["collected_data"]


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_low_property_value_is_rejected_immediately(client: TestClient) -> None:
    session_id = "low-property-value-session"
    prompts = [
        "I want a quote for home insurance",
        "house",
        "Austin",
    ]
    for message in prompts:
        _post_chat(client, session_id, message)

    events = _post_chat(client, session_id, "100")
    message = events[-1]["data"]["message"].lower()

    assert "more realistic property value" in message
    assert main.SESSION_STORE[session_id]["current_field"] == "estimated_value"
    assert "estimated_value" not in main.SESSION_STORE[session_id]["collected_data"]


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_zoo_is_rejected_as_location(client: TestClient) -> None:
    session_id = "zoo-location-session"

    _post_chat(client, session_id, "I want a quote for home insurance")
    _post_chat(client, session_id, "house")
    events = _post_chat(client, session_id, "zoo")

    message = events[-1]["data"]["message"].lower()
    assert "real city or location" in message
    assert main.SESSION_STORE[session_id]["current_field"] == "location"
    assert "location" not in main.SESSION_STORE[session_id]["collected_data"]


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_invalid_boolean_input_is_rejected_for_life_smoker_field(client: TestClient) -> None:
    session_id = "invalid-bool-session"
    prompts = [
        "I want a quote for life insurance",
        "42",
        "good",
    ]
    for message in prompts:
        _post_chat(client, session_id, message)

    events = _post_chat(client, session_id, "sometimes")
    message = events[-1]["data"]["message"].lower()

    assert "please reply yes or no" in message
    assert main.SESSION_STORE[session_id]["current_field"] == "smoker"
    assert "smoker" not in main.SESSION_STORE[session_id]["collected_data"]


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_invalid_term_length_is_rejected_for_life_quote(client: TestClient) -> None:
    session_id = "invalid-term-session"
    prompts = [
        "I want a quote for life insurance",
        "42",
        "good",
        "no",
        "500000",
    ]
    for message in prompts:
        _post_chat(client, session_id, message)

    events = _post_chat(client, session_id, "15")
    message = events[-1]["data"]["message"].lower()

    assert "please choose one of: 10, 20, 30" in message
    assert main.SESSION_STORE[session_id]["current_field"] == "term_years"
    assert "term_years" not in main.SESSION_STORE[session_id]["collected_data"]


def test_quote_flow_starts_in_identify_mode_instead_of_rag(client: TestClient) -> None:
    session_id = "start-quote-session"

    events = _post_chat(client, session_id, "I'd like to book an appointment")
    payload = events[-1]["data"]

    # P2 "book" → start_intake → identify_service → dental service prompt
    assert "which service would you like to book" in payload["message"].lower()
    assert payload["session"]["mode"] == "transactional"
    assert payload["session"]["intake_step"] == "identify"
    assert payload["session"]["service_type"] is None


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_home_product_selection_advances_to_first_field(client: TestClient) -> None:
    session_id = "home-product-selection-session"

    _post_chat(client, session_id, "I want a quote")
    events = _post_chat(client, session_id, "home")

    payload = events[-1]["data"]
    assert payload["message"] == "Is the property a house, condo, or apartment?"
    assert payload["session"]["mode"] == "transactional"
    assert payload["session"]["intake_step"] == "collect"
    assert payload["session"]["service_type"] == "home"


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_motor_alias_selects_auto_quote_product(client: TestClient) -> None:
    session_id = "motor-product-selection-session"

    _post_chat(client, session_id, "I want a quote")
    events = _post_chat(client, session_id, "motor")

    payload = events[-1]["data"]
    assert payload["message"] == "What year is the vehicle? (e.g. 2019)"
    assert payload["session"]["mode"] == "transactional"
    assert payload["session"]["intake_step"] == "collect"
    assert payload["session"]["service_type"] == "auto"


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_invalid_text_reply_during_numeric_auto_field_does_not_leave_quote_flow(client: TestClient) -> None:
    session_id = "invalid-text-auto-field-session"

    _post_chat(client, session_id, "I want a quote for auto insurance")
    first_retry = _post_chat(client, session_id, "motor")
    second_retry = _post_chat(client, session_id, "yes continue")

    first_message = first_retry[-1]["data"]["message"].lower()
    second_message = second_retry[-1]["data"]["message"].lower()

    assert "please enter a whole number" in first_message
    assert "what year is the vehicle?" in first_message
    assert "please enter a whole number" in second_message
    assert "what year is the vehicle?" in second_message
    assert main.SESSION_STORE[session_id]["intake_step"] == "collect"
    assert main.SESSION_STORE[session_id]["current_field"] == "vehicle_year"
    assert main.SESSION_STORE[session_id]["service_type"] == "auto"
    assert main.SESSION_STORE[session_id]["collected_data"] == {}


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_invalid_year_built_does_not_advance_to_coverage_level(client: TestClient) -> None:
    session_id = "invalid-year-built-session"
    prompts = [
        "I want a quote for home insurance",
        "house",
        "Makati",
        "350000",
    ]
    for message in prompts:
        _post_chat(client, session_id, message)

    events = _post_chat(client, session_id, "100")
    message = events[-1]["data"]["message"].lower()

    assert "year built must be between 1801" in message
    assert main.SESSION_STORE[session_id]["current_field"] == "year_built"
    assert main.SESSION_STORE[session_id]["intake_step"] == "collect"
    assert "year_built" not in main.SESSION_STORE[session_id]["collected_data"]


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_adjust_reopens_collection_from_first_field(client: TestClient) -> None:
    session_id = "adjust-session"
    prompts = [
        "I want a quote for auto insurance",
        "2019",
        "Toyota",
        "Camry",
        "35",
        "0",
        "standard",
    ]
    for message in prompts:
        _post_chat(client, session_id, message)

    events = _post_chat(client, session_id, "adjust")
    message = events[-1]["data"]["message"]

    assert message == "What year is the vehicle? (e.g. 2019)"
    assert main.SESSION_STORE[session_id]["booking_result"] is None
    assert main.SESSION_STORE[session_id]["current_field"] == "vehicle_year"
    assert main.SESSION_STORE[session_id]["collected_data"] == {}


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_implausible_accident_count_is_rejected_before_quote_generation(client: TestClient) -> None:
    session_id = "implausible-accidents-session"
    prompts = [
        "I want a quote for auto insurance",
        "2019",
        "Toyota",
        "Camry",
        "29",
    ]
    for message in prompts:
        _post_chat(client, session_id, message)

    events = _post_chat(client, session_id, "24")
    message = events[-1]["data"]["message"].lower()

    assert "realistic accident count between 0 and 10" in message
    assert main.SESSION_STORE[session_id]["current_field"] == "accidents_last_5yr"
    assert "accidents_last_5yr" not in main.SESSION_STORE[session_id]["collected_data"]


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


@pytest.mark.skip(reason="migrating to dental in tasks 4-6")
def test_switching_product_mid_flow_resets_to_new_product(client: TestClient) -> None:
    session_id = "switch-product-session"

    _post_chat(client, session_id, "I want a quote for auto insurance")
    _post_chat(client, session_id, "2019")
    events = _post_chat(client, session_id, "I want a quote for home insurance")

    assert events[-1]["data"]["message"] == "Is the property a house, condo, or apartment?"
    state = main.SESSION_STORE[session_id]
    assert state["service_type"] == "home"
    assert state["current_field"] == "property_type"
    assert state["collected_data"] == {}


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

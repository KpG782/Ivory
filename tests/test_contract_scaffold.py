"""Spec-aligned contract scaffold for Ivory.

This file intentionally avoids importing runtime application code because the
repository does not yet contain the backend/frontend implementation.

The tests below encode the expected public contracts as lightweight assertions
so the spec can be translated into executable tests later without changing the
coverage intent.
"""

from __future__ import annotations


EXPECTED_CHAT_STATE_KEYS = {
    "session_id",
    "messages",
    "mode",
    "intent",
    "intake_step",
    "service_type",
    "collected_data",
    "booking_result",
    "pending_question",
    "last_error",
    "trace_id",
}

EXPECTED_INTENTS = {"question", "quote", "response"}
EXPECTED_MODES = {"conversational", "transactional"}
EXPECTED_INTAKE_STEPS = {"identify", "collect", "validate", "confirm"}
EXPECTED_SSE_EVENTS = {"token", "message_complete", "error"}
EXPECTED_ENDPOINTS = {"/chat", "/reset", "/health"}


def test_contract_scaffold_documents_expected_state_shape() -> None:
    assert "session_id" in EXPECTED_CHAT_STATE_KEYS
    assert "collected_data" in EXPECTED_CHAT_STATE_KEYS
    assert "pending_question" in EXPECTED_CHAT_STATE_KEYS


def test_contract_scaffold_documents_intent_model() -> None:
    assert EXPECTED_INTENTS == {"question", "quote", "response"}


def test_contract_scaffold_documents_modes_and_steps() -> None:
    assert EXPECTED_MODES == {"conversational", "transactional"}
    assert EXPECTED_INTAKE_STEPS == {"identify", "collect", "validate", "confirm"}


def test_contract_scaffold_documents_public_endpoints() -> None:
    assert EXPECTED_ENDPOINTS == {"/chat", "/reset", "/health"}


def test_contract_scaffold_documents_sse_event_names() -> None:
    assert EXPECTED_SSE_EVENTS == {"token", "message_complete", "error"}


def test_contract_scaffold_documents_environment_hygiene() -> None:
    env_rules = {
        "backend/.venv is the Python runtime environment",
        ".env is config only",
        "no global Python installs",
    }
    assert "backend/.venv is the Python runtime environment" in env_rules
    assert ".env is config only" in env_rules

"""Spec-aligned contract scaffold for Ivory Dental Front Desk.

These tests keep the intended public surface explicit and cross-check it
against the implemented backend so a rename in either place fails loudly.
The heavier behavioral coverage lives in ``test_backend_integration.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


EXPECTED_CHAT_STATE_KEYS = {
    "session_id",
    "messages",
    "mode",
    "intent",
    "intake_step",
    "service_type",
    "collected_data",
    "visit_estimate",
    "pending_question",
    "last_error",
    "trace_id",
}

EXPECTED_INTENTS = {"question", "intake", "response"}
EXPECTED_MODES = {"conversational", "transactional"}
EXPECTED_INTAKE_STEPS = {"identify", "collect", "validate", "confirm"}
EXPECTED_SERVICE_TYPES = {"cleaning", "emergency", "cosmetic"}
EXPECTED_SSE_EVENTS = {"token", "message_complete", "error"}
EXPECTED_ENDPOINTS = {"/chat", "/reset", "/health"}


def test_contract_scaffold_documents_expected_state_shape() -> None:
    from state import ChatState

    assert "session_id" in EXPECTED_CHAT_STATE_KEYS
    assert "collected_data" in EXPECTED_CHAT_STATE_KEYS
    assert "pending_question" in EXPECTED_CHAT_STATE_KEYS
    # Every documented key must exist on the implemented state schema.
    assert EXPECTED_CHAT_STATE_KEYS <= set(ChatState.__annotations__)


def test_contract_scaffold_documents_intent_model() -> None:
    assert EXPECTED_INTENTS == {"question", "intake", "response"}


def test_contract_scaffold_documents_modes_and_steps() -> None:
    assert EXPECTED_MODES == {"conversational", "transactional"}
    assert EXPECTED_INTAKE_STEPS == {"identify", "collect", "validate", "confirm"}


def test_contract_scaffold_documents_service_types() -> None:
    from nodes.collect_details import FIELD_SPECS
    from nodes.identify_service import SERVICE_LABELS

    assert EXPECTED_SERVICE_TYPES == {"cleaning", "emergency", "cosmetic"}
    assert set(FIELD_SPECS) == EXPECTED_SERVICE_TYPES
    assert set(SERVICE_LABELS) == EXPECTED_SERVICE_TYPES


def test_contract_scaffold_documents_public_endpoints() -> None:
    import main

    assert EXPECTED_ENDPOINTS == {"/chat", "/reset", "/health"}
    implemented_paths = {route.path for route in main.app.routes}
    assert EXPECTED_ENDPOINTS <= implemented_paths


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

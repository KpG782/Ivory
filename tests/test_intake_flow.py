"""End-to-end tests for Task 6: validate_intake + confirm verbs.

Uses the shared `client` fixture, `_parse_sse_body`, and `_post_chat`
from conftest.py.
"""
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
from conftest import _parse_sse_body, _post_chat


# ── Tiny per-file helpers ──────────────────────────────────────────────────────

def _send(client: TestClient, session_id: str, message: str) -> str:
    """Post a chat message and return the final assistant text."""
    events = _post_chat(client, session_id, message)
    return events[-1]["data"]["message"]



def _drive_to_confirm(client: TestClient, session_id: str) -> str:
    """Drive a full cleaning intake to the confirm step; return final reply."""
    _send(client, session_id, "book a cleaning")
    _send(client, session_id, "Maria Santos")
    _send(client, session_id, "9175550144")
    _send(client, session_id, "maria@example.com")
    _send(client, session_id, "new")
    return _send(client, session_id, "Wednesday 2:30 pm")


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_full_intake_reaches_confirm(client: TestClient) -> None:
    """All five fields accepted → validate_intake fires → intake_step == confirm."""
    sid = "t-intake-1"
    reply = _drive_to_confirm(client, sid)

    state = main.SESSION_STORE[sid]
    assert state["intake_step"] == "confirm", f"Expected confirm, got {state['intake_step']!r}"
    assert "Maria Santos" in reply
    assert "cleaning" in reply.lower()


def test_confirm_summary_contains_service_label(client: TestClient) -> None:
    """The confirmation message uses the human-readable service label."""
    sid = "t-intake-label"
    reply = _drive_to_confirm(client, sid)

    # SERVICES["cleaning"]["label"] == "Cleaning & checkup"
    assert "Cleaning" in reply


def test_confirm_summary_contains_time_details(client: TestClient) -> None:
    """The summary includes weekday + time — Wednesday 2:30 PM."""
    sid = "t-intake-time"
    reply = _drive_to_confirm(client, sid)

    assert "Wednesday" in reply
    assert "2:30" in reply


def test_confirm_summary_contains_phone_and_email(client: TestClient) -> None:
    """The summary includes the phone number and e-mail address."""
    sid = "t-intake-contact"
    reply = _drive_to_confirm(client, sid)

    assert "9175550144" in reply
    assert "maria@example.com" in reply


def test_accept_after_confirm_reaches_booked(client: TestClient) -> None:
    """accept verb after a valid confirm summary → intake_step == booked."""
    sid = "t-accept-1"
    _drive_to_confirm(client, sid)

    reply = _send(client, sid, "accept")
    state = main.SESSION_STORE[sid]

    assert state["intake_step"] == "booked", f"Expected booked, got {state['intake_step']!r}"
    assert state["mode"] == "conversational"
    assert state["current_field"] is None
    assert "Maria Santos" in reply


def test_accept_without_confirm_returns_guidance(client: TestClient) -> None:
    """accept sent from confirm step when intake_step != 'confirm' → guidance message."""
    sid = "t-accept-no-confirm"
    # Drive to the confirm node by being at confirm step with intake_step == "identify"
    # (router P4 only fires when step == "confirm"; from "identify" accept → identify route)
    # Instead, directly verify confirm node behaviour via unit test on the node.
    from nodes.confirm import confirm as confirm_node

    state: dict[str, Any] = {
        "messages": [],
        "intake_step": "collect",     # not "confirm"
        "mode": "transactional",
        "service_type": "cleaning",
        "collected_data": {},
        "current_field": "patient_name",
        "booking_result": None,
    }
    result = confirm_node(state, "accept")
    reply = result["messages"][-1]["content"]

    assert "nothing ready" in reply.lower() or "book" in reply.lower() or "confirm" in reply.lower()
    assert result["intake_step"] != "booked"


def test_adjust_after_confirm_restarts_collection(client: TestClient) -> None:
    """adjust verb after confirm → collected_data == {}, back to patient_name prompt."""
    sid = "t-adjust-1"
    _drive_to_confirm(client, sid)

    reply = _send(client, sid, "adjust")
    state = main.SESSION_STORE[sid]

    assert state["collected_data"] == {}, f"Expected empty collected_data, got {state['collected_data']}"
    assert state["current_field"] == "patient_name", f"Expected patient_name, got {state['current_field']!r}"
    assert "may i have your full name" in reply.lower()


def test_restart_after_confirm_goes_to_identify(client: TestClient) -> None:
    """restart verb resets all intake state and prompts for service selection."""
    sid = "t-restart-1"
    _drive_to_confirm(client, sid)

    reply = _send(client, sid, "restart")
    state = main.SESSION_STORE[sid]

    assert state["intake_step"] == "identify"
    assert state["service_type"] is None
    assert state["collected_data"] == {}
    assert "which service" in reply.lower() or "cleaning" in reply.lower()


def test_validate_intake_defense_rejects_corrupted_field() -> None:
    """validate_intake unit test: a corrupted collected_data triggers re-collection."""
    from nodes.validate_intake import validate_intake

    state: dict[str, Any] = {
        "service_type": "cleaning",
        "collected_data": {
            "patient_name": "Maria Santos",
            "phone": "not-a-phone",       # bad value that bypassed collect
            "email": "maria@example.com",
            "patient_status": "new",
            "preferred_slot": "2026-06-18T14:30:00",
        },
        "messages": [],
        "intake_step": "validate",
        "current_field": None,
    }

    result = validate_intake(state)

    assert result["intake_step"] == "collect"
    assert result["current_field"] == "phone"
    assert "phone" not in result["collected_data"]
    last_msg = result["messages"][-1]["content"]
    assert "phone" in last_msg.lower() or "area code" in last_msg.lower()

"""Task 7: Tests for mock tools layer and book_appointment node.

Integration tests use the shared `client` fixture from conftest.py.
Unit tests for book_appointment use stub ToolBundles (injected, not monkeypatched).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import main
from conftest import _parse_sse_body, _post_chat


# ── Tiny helpers ──────────────────────────────────────────────────────────────

def _send(client: TestClient, session_id: str, message: str) -> str:
    """Post a chat message and return the final assistant text."""
    events = _post_chat(client, session_id, message)
    return events[-1]["data"]["message"]


def _snapshot(client: TestClient, session_id: str) -> dict[str, Any]:
    """Return the raw SESSION_STORE state for a session."""
    return dict(main.SESSION_STORE[session_id])


def _booking_uid(client: TestClient, session_id: str) -> str | None:
    snap = _snapshot(client, session_id)
    br = snap.get("booking_result") or {}
    return br.get("booking_uid")


def _drive_to_confirm(client: TestClient, session_id: str, slot: str = "Wednesday 2:30 pm") -> str:
    """Drive a full cleaning intake to the confirm step; returns session_id."""
    _send(client, session_id, "book a cleaning")
    _send(client, session_id, "Maria Santos")
    _send(client, session_id, "9175550144")
    _send(client, session_id, "maria@example.com")
    _send(client, session_id, "new")
    _send(client, session_id, slot)
    return session_id


# ── Integration tests ─────────────────────────────────────────────────────────

def test_accept_books_and_reports(client: TestClient) -> None:
    """accept after confirm → booked state, booking_result set, message contains email."""
    sid = "booking-accept-1"
    _drive_to_confirm(client, sid)
    reply = _send(client, sid, "accept")
    snap = _snapshot(client, sid)

    assert snap["intake_step"] == "booked"
    assert bool(snap["booking_result"]) is True
    assert "booked" in reply.lower()
    assert "maria@example.com" in reply


def test_accept_is_idempotent(client: TestClient) -> None:
    """Double-accept: second accept re-emits the booking summary without creating a duplicate."""
    sid = "booking-idempotent-1"
    _drive_to_confirm(client, sid)
    first_reply = _send(client, sid, "accept")
    uid1 = _booking_uid(client, sid)

    # User double-sends accept — must re-emit success, not fall through to RAG.
    second_reply = _send(client, sid, "accept")
    uid2 = _booking_uid(client, sid)

    assert uid1 is not None
    assert uid1 == uid2  # no double-booking
    # Second reply must re-state the booking, not give a generic/nonsense answer.
    assert "booked" in second_reply.lower(), (
        f"Second-accept reply did not re-state the booking: {second_reply!r}"
    )
    assert "maria@example.com" in second_reply or uid1 in second_reply, (
        f"Second-accept reply is missing email/uid context: {second_reply!r}"
    )


def test_unavailable_slot_keeps_confirm_state(client: TestClient) -> None:
    """Friday slot → availability check fails → intake_step stays confirm, message offers retry."""
    sid = "booking-unavailable-1"
    _drive_to_confirm(client, sid, slot="Friday 2:30 pm")
    reply = _send(client, sid, "accept")
    snap = _snapshot(client, sid)

    assert snap["intake_step"] == "confirm"
    assert "taken" in reply.lower() or "another time" in reply.lower()


# ── Unit tests for book_appointment with stub ToolBundles ─────────────────────

def _make_state(slot: str = "2026-06-18T14:30:00") -> dict[str, Any]:
    """Return a minimal state dict at the confirm step."""
    return {
        "session_id": "unit-test-session",
        "messages": [],
        "intake_step": "confirm",
        "mode": "transactional",
        "service_type": "cleaning",
        "collected_data": {
            "patient_name": "Maria Santos",
            "phone": "9175550144",
            "email": "maria@example.com",
            "patient_status": "new",
            "preferred_slot": slot,
        },
        "booking_result": None,
        "current_field": None,
    }


def _stub_bundle(
    *,
    availability_ok: bool = True,
    booking_ok: bool = True,
    crm_ok: bool = True,
    email_ok: bool = True,
    booking_uid: str = "mock_test0001",
    lead_record_id: str = "rec_test0001",
) -> Any:
    """Build an injectable ToolBundle with controllable outcomes."""
    from tools.base import ToolBundle, ToolResult

    booking = MagicMock()
    booking.check_availability.return_value = (
        ToolResult(ok=True, data={"available": True})
        if availability_ok
        else ToolResult(ok=False, error="Unavailable")
    )
    booking.create_booking.return_value = (
        ToolResult(ok=True, data={"booking_uid": booking_uid})
        if booking_ok
        else ToolResult(ok=False, error="Booking failed")
    )

    crm = MagicMock()
    crm.upsert_lead.return_value = (
        ToolResult(ok=True, data={"lead_record_id": lead_record_id})
        if crm_ok
        else ToolResult(ok=False, error="CRM failed")
    )

    email = MagicMock()
    email.send_confirmation.return_value = (
        ToolResult(ok=True, data={"message_id": "msg_001"})
        if email_ok
        else ToolResult(ok=False, error="Email failed")
    )

    return ToolBundle(booking=booking, crm=crm, email=email)


def test_unit_booking_tool_fails_stays_confirm() -> None:
    """booking.create_booking fails → intake_step stays confirm, no booking_result."""
    from nodes.book_appointment import book_appointment

    state = _make_state()
    tools = _stub_bundle(booking_ok=False)
    result = book_appointment(state, tools=tools)

    assert result["intake_step"] == "confirm"
    assert not result.get("booking_result") or not result["booking_result"].get("booking_uid")
    last_msg = result["messages"][-1]["content"].lower()
    assert "taken" in last_msg or "another time" in last_msg


def test_unit_availability_fails_stays_confirm() -> None:
    """check_availability returns not-ok → intake_step stays confirm."""
    from nodes.book_appointment import book_appointment

    state = _make_state()
    tools = _stub_bundle(availability_ok=False)
    result = book_appointment(state, tools=tools)

    assert result["intake_step"] == "confirm"
    tools.booking.create_booking.assert_not_called()


def test_unit_crm_fails_booking_stands() -> None:
    """CRM fails after booking succeeds → booking stands, lead_record_id None, message confirms."""
    from nodes.book_appointment import book_appointment

    state = _make_state()
    tools = _stub_bundle(crm_ok=False, booking_uid="mock_crm_fail")
    result = book_appointment(state, tools=tools)

    assert result["intake_step"] == "booked"
    br = result["booking_result"]
    assert br is not None
    assert br["booking_uid"] == "mock_crm_fail"
    assert br["lead_record_id"] is None
    # Message still confirms booking
    last_msg = result["messages"][-1]["content"].lower()
    assert "booked" in last_msg


def test_unit_email_fails_message_is_honest() -> None:
    """Email fails after booking+CRM succeed → confirmation_email='failed', message is honest."""
    from nodes.book_appointment import book_appointment

    state = _make_state()
    tools = _stub_bundle(email_ok=False, booking_uid="mock_email_fail")
    result = book_appointment(state, tools=tools)

    assert result["intake_step"] == "booked"
    br = result["booking_result"]
    assert br is not None
    assert br["booking_uid"] == "mock_email_fail"
    assert br["confirmation_email"] == "failed"
    last_msg = result["messages"][-1]["content"].lower()
    assert "didn't go through" in last_msg or "confirmation email" in last_msg


def test_unit_idempotency_no_double_booking() -> None:
    """State already has booking_result with booking_uid → short-circuit, create_booking not called."""
    from nodes.book_appointment import book_appointment

    state = _make_state()
    state["booking_result"] = {
        "service": "cleaning",
        "start_time": "2026-06-18T14:30:00",
        "patient_name": "Maria Santos",
        "booking_uid": "mock_existing001",
        "lead_record_id": "rec_existing001",
        "confirmation_email": "sent",
        "summary": "Cleaning & checkup on Wednesday Jun 18, 2:30 PM for Maria Santos",
    }
    state["intake_step"] = "booked"  # already booked

    tools = _stub_bundle()
    result = book_appointment(state, tools=tools)

    # Tool must NOT have been called
    tools.booking.create_booking.assert_not_called()
    # State unchanged
    assert result["booking_result"]["booking_uid"] == "mock_existing001"
    # Message re-emits success
    last_msg = result["messages"][-1]["content"].lower()
    assert "booked" in last_msg


# ── Post-booking CTA integration tests ───────────────────────────────────────

def _drive_to_booked(client: TestClient, session_id: str) -> str:
    """Drive a full cleaning intake all the way to the booked state; returns session_id."""
    _drive_to_confirm(client, session_id)
    _send(client, session_id, "accept")
    snap = _snapshot(client, session_id)
    assert snap["intake_step"] == "booked", f"Expected booked, got {snap['intake_step']!r}"
    return session_id


def test_restart_after_booked_resets_intake(client: TestClient) -> None:
    """book → accept → 'restart' → dental service question; state fully reset.

    Issue 1 fix: P1 in the router now fires when intake_step == 'booked' even
    though mode has returned to 'conversational'. The confirm node's restart
    branch (_reset_intake_state) clears booking_result and collected_data.
    """
    sid = "post-book-restart-1"
    _drive_to_booked(client, sid)
    reply = _send(client, sid, "restart")
    snap = _snapshot(client, sid)

    # State must be fully reset
    assert snap["intake_step"] == "identify", f"intake_step={snap['intake_step']!r}"
    assert snap.get("collected_data") == {} or snap.get("collected_data") is None
    assert snap.get("booking_result") is None
    # Reply must ask which service to book
    assert any(word in reply.lower() for word in ("cleaning", "whitening", "consultation", "emergency", "service")), (
        f"Reply did not ask for a service: {reply!r}"
    )


def test_book_another_appointment_after_booked_fresh_start(client: TestClient) -> None:
    """book → accept → 'book another appointment' → fresh intake; collected_data empty.

    Issue 2 fix: _apply_service_switch detects intake_step == 'booked' and
    calls _reset_intake_progress before routing to start_intake/identify_service,
    so the stale collected_data and booking_result don't survive.
    """
    sid = "post-book-another-1"
    _drive_to_booked(client, sid)
    reply = _send(client, sid, "book another appointment")
    snap = _snapshot(client, sid)

    assert snap.get("collected_data") in ({}, None), (
        f"collected_data was not cleared: {snap.get('collected_data')!r}"
    )
    assert snap.get("booking_result") is None, (
        f"booking_result was not cleared: {snap.get('booking_result')!r}"
    )
    assert snap["intake_step"] == "identify", f"intake_step={snap['intake_step']!r}"
    # Reply should ask which service to book
    assert any(word in reply.lower() for word in ("cleaning", "whitening", "consultation", "emergency", "service", "book")), (
        f"Reply did not re-initiate intake: {reply!r}"
    )


def test_book_whitening_after_booked_pre_selects_service(client: TestClient) -> None:
    """book → accept → 'book a whitening' → service_type whitening, fresh collect.

    Issue 2 fix (variant): when a service name appears in the post-booked booking
    request, _apply_service_switch sets service_type and identify_service advances
    straight to collect with an empty collected_data.
    """
    sid = "post-book-whitening-1"
    _drive_to_booked(client, sid)
    reply = _send(client, sid, "book a whitening")
    snap = _snapshot(client, sid)

    assert snap.get("collected_data") in ({}, None), (
        f"collected_data was not cleared: {snap.get('collected_data')!r}"
    )
    assert snap.get("booking_result") is None, (
        f"booking_result was not cleared: {snap.get('booking_result')!r}"
    )
    assert snap.get("service_type") == "whitening", (
        f"service_type={snap.get('service_type')!r}"
    )
    assert snap["intake_step"] == "collect", (
        f"intake_step={snap['intake_step']!r}"
    )
    # First collect prompt is always the patient name
    assert "name" in reply.lower(), f"Expected name prompt, got: {reply!r}"


def test_adjust_after_booked_returns_already_booked_message(client: TestClient) -> None:
    """book → accept → 'adjust' → reply contains 'already booked'.

    Issue 3 fix: P3b now matches ADJUST_HINTS (without '?') so the router
    sends 'adjust' to confirm, which has a booked+adjust branch.
    """
    sid = "post-book-adjust-1"
    _drive_to_booked(client, sid)
    reply = _send(client, sid, "adjust")

    assert "already booked" in reply.lower() or "restart" in reply.lower(), (
        f"Expected 'already booked' nudge, got: {reply!r}"
    )

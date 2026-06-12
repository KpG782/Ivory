"""book_appointment node — the ONLY importer of registry.get_tools() in the graph.

Sequence:
  1. Idempotency: if booking_result already has a booking_uid, re-emit the
     success summary without calling any tool.
  2. Parse slot; check_availability — if not ok, stay at confirm with "slot taken"
     message.
  3. create_booking — same abort path on failure.
  4. Write booking_result immediately (idempotency anchor).
  5. upsert_lead — degrade on failure (lead_record_id stays None).
  6. send_confirmation — degrade on failure (confirmation_email = "failed").
  7. Final message; set intake_step = "booked".
"""
from __future__ import annotations

from datetime import datetime

from nodes.validate_intake import humanize_slot
from services.catalog import SERVICES
from tools.base import ToolBundle
from tools.registry import get_tools


def book_appointment(state: dict, tools: ToolBundle | None = None) -> dict:
    if tools is None:
        tools = get_tools()

    collected = state.get("collected_data", {})
    service = state.get("service_type", "")
    service_label = SERVICES.get(service, {}).get("label", service)
    patient_name = collected.get("patient_name", "")
    email = collected.get("email", "")
    phone = collected.get("phone", "")
    patient_status = collected.get("patient_status", "")
    slot_iso = collected.get("preferred_slot", "")
    session_id = state.get("session_id", "")

    # ── 1. Idempotency ────────────────────────────────────────────────────────
    existing = state.get("booking_result") or {}
    if existing.get("booking_uid"):
        # Re-emit success without touching tools.
        _append_assistant_message(state, _success_message(existing, email))
        state["intake_step"] = "booked"
        state["mode"] = "conversational"
        state["current_field"] = None
        return state

    # ── 2. Parse slot + check availability ────────────────────────────────────
    try:
        start = datetime.fromisoformat(slot_iso)
    except (ValueError, TypeError):
        _append_assistant_message(
            state,
            "Something went wrong reading your requested time — please reply "
            "**adjust** to re-enter it.",
        )
        state["intake_step"] = "confirm"
        return state

    avail = tools.booking.check_availability(service, start)
    if not avail.ok:
        _append_assistant_message(
            state,
            "That time was just taken — what other day and time work for you? "
            "You can also reply **adjust** or **restart**.",
        )
        state["intake_step"] = "confirm"
        return state

    # ── 3. Create booking ─────────────────────────────────────────────────────
    booking_result = tools.booking.create_booking(service, start, patient_name, email)
    if not booking_result.ok:
        _append_assistant_message(
            state,
            "That time was just taken — what other day and time work for you? "
            "You can also reply **adjust** or **restart**.",
        )
        state["intake_step"] = "confirm"
        return state

    booking_uid = booking_result.data["booking_uid"]
    time_str = humanize_slot(slot_iso)
    summary = f"{service_label} on {time_str.replace(' at ', ', ')} for {patient_name}"

    # ── 4. Write booking_result (idempotency anchor) ──────────────────────────
    result: dict = {
        "service": service,
        "start_time": slot_iso,
        "patient_name": patient_name,
        "booking_uid": booking_uid,
        "lead_record_id": None,
        "confirmation_email": "skipped",
        "summary": summary,
    }
    state["booking_result"] = result

    # ── 5. Upsert lead (degrade on failure) ───────────────────────────────────
    lead = {
        "session_id": session_id,
        "name": patient_name,
        "phone": phone,
        "email": email,
        "service": service,
        "preferred_slot": slot_iso,
        "status": "booked",
        "booking_uid": booking_uid,
        "patient_status": patient_status,
    }
    crm_result = tools.crm.upsert_lead(lead)
    if crm_result.ok:
        result["lead_record_id"] = crm_result.data.get("lead_record_id")
        state["booking_result"] = result

    # ── 6. Send confirmation email (degrade on failure) ────────────────────────
    email_result = tools.email.send_confirmation(email, result)
    if email_result.ok:
        result["confirmation_email"] = "sent"
    else:
        result["confirmation_email"] = "failed"
    state["booking_result"] = result

    # ── 7. Final message ──────────────────────────────────────────────────────
    _append_assistant_message(state, _success_message(result, email))
    state["intake_step"] = "booked"
    state["mode"] = "conversational"
    state["current_field"] = None
    return state


def _success_message(booking_result: dict, email: str) -> str:
    summary = booking_result.get("summary", "your appointment")
    email_status = booking_result.get("confirmation_email", "skipped")
    if email_status == "sent":
        return (
            f"You're booked: {summary}. "
            f"A confirmation is on its way to {email}. "
            "Reply restart if you'd like to book another appointment."
        )
    elif email_status == "failed":
        return (
            f"You're booked: {summary}. "
            f"Though the confirmation email didn't go through — please save this: {summary}. "
            "Reply restart if you'd like to book another appointment."
        )
    else:
        return (
            f"You're booked: {summary}. "
            "Reply restart if you'd like to book another appointment."
        )


def _append_assistant_message(state: dict, content: str) -> None:
    messages = list(state.get("messages", []))
    messages.append({"role": "assistant", "content": content})
    state["messages"] = messages

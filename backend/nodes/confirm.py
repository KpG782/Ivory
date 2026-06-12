from __future__ import annotations

from datetime import datetime

from nodes.router import interpret_confirmation
from services.catalog import SERVICES


def confirm(state: dict, message: str) -> dict:
    action = interpret_confirmation(message)

    if action == "accept":
        if state.get("intake_step") != "confirm":
            _append_assistant_message(
                state,
                "There is nothing ready to confirm yet. "
                "Please complete the booking details first, or say which service you'd like to book.",
            )
            state["mode"] = "transactional"
            state["intake_step"] = state.get("intake_step") or "identify"
            return state

        # Build a readable placeholder confirmation.
        collected = state.get("collected_data", {})
        service = state.get("service_type", "")
        service_label = SERVICES.get(service, {}).get("label", service)
        patient_name = collected.get("patient_name", "you")
        slot_iso = collected.get("preferred_slot")
        time_str = ""
        if slot_iso:
            try:
                dt = datetime.fromisoformat(slot_iso)
                weekday = dt.strftime("%A")
                month = dt.strftime("%b")
                day = str(dt.day)
                hour_12 = dt.hour % 12 or 12
                minute = dt.strftime("%M")
                ampm = "AM" if dt.hour < 12 else "PM"
                time_str = f" on {weekday} {month} {day} at {hour_12}:{minute} {ampm}"
            except ValueError:
                pass

        _append_assistant_message(
            state,
            f"You're booked: {service_label} for {patient_name}{time_str}. "
            "(Booking confirmation wiring lands with the tools layer.) "
            "Reply restart if you want to begin another booking.",
        )
        state["mode"] = "conversational"
        state["intake_step"] = "booked"
        state["current_field"] = None
        return state

    if action == "adjust":
        service_type = state.get("service_type")
        state["intake_step"] = "collect"
        state["current_field"] = None
        state["collected_data"] = {}
        state["booking_result"] = None
        state["mode"] = "transactional"
        state["service_type"] = service_type
        return state

    if action == "restart":
        _reset_intake_state(state)
        _append_assistant_message(
            state,
            "The intake flow has been restarted. Which service would you like to book: "
            "cleaning, consultation, whitening — or is this an emergency?",
        )
        return state

    _append_assistant_message(
        state,
        "Please reply accept, adjust, or restart so I know how to handle the booking.",
    )
    return state


def _reset_intake_state(state: dict) -> None:
    state["mode"] = "transactional"
    state["intake_step"] = "identify"
    state["service_type"] = None
    state["collected_data"] = {}
    state["booking_result"] = None
    state["pending_question"] = None
    state["current_field"] = None
    state["last_error"] = None


def _append_assistant_message(state: dict, content: str) -> None:
    messages = list(state.get("messages", []))
    messages.append({"role": "assistant", "content": content})
    state["messages"] = messages

from __future__ import annotations

from nodes.router import interpret_confirmation


def confirm(state: dict, message: str) -> dict:
    action = interpret_confirmation(message)
    booking_result = state.get("booking_result")

    if action == "accept" and not booking_result:
        _append_assistant_message(
            state,
            "There is no booking ready to confirm yet. Please complete the booking details first.",
        )
        state["mode"] = "transactional"
        state["intake_step"] = "collect" if state.get("service_type") else "identify"
        return state

    if action == "accept":
        booking_result = booking_result or {}
        summary = booking_result.get("summary", "your booking")
        _append_assistant_message(
            state,
            f"Confirmed. I have finalized {summary}. Reply restart if you want to begin another booking.",
        )
        state["mode"] = "conversational"
        state["intake_step"] = "identify"
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
            "The intake flow has been restarted. Which service would you like to book: cleaning, consultation, whitening — or is this an emergency?",
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

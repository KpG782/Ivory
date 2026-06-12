from __future__ import annotations

from nodes.router import interpret_confirmation


def confirm(state: dict, message: str) -> dict:
    action = interpret_confirmation(message)

    if action == "accept":
        if state.get("intake_step") == "booked":
            # Booking already exists — user re-sent an affirmation.
            # Route to book_appointment so its idempotency guard re-emits
            # the success summary without calling any tool again.
            booking_result = state.get("booking_result") or {}
            if booking_result.get("booking_uid"):
                state["route"] = "book"
                return state
            # booking_result missing uid despite booked step — shouldn't happen,
            # but fall through to the normal "nothing to confirm" path.

        if state.get("intake_step") != "confirm":
            _append_assistant_message(
                state,
                "There is nothing ready to confirm yet. "
                "Please complete the booking details first, or say which service you'd like to book.",
            )
            state["mode"] = "transactional"
            state["intake_step"] = state.get("intake_step") or "identify"
            return state

        # Signal the router to invoke book_appointment on the next edge.
        # book_appointment decides success/failure state and appends the final message.
        state["route"] = "book"
        return state

    if action == "adjust":
        if state.get("intake_step") == "booked":
            _append_assistant_message(
                state,
                "You're already booked — reply **restart** to begin a new booking.",
            )
            return state

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

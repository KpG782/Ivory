from __future__ import annotations

from services.quote_calculator import calculate_quote, validate_quote_inputs


def validate_quote(state: dict, message: str | None = None) -> dict:
    service_type = state.get("service_type")
    collected_data = dict(state.get("collected_data", {}))

    validation = validate_quote_inputs(service_type, collected_data)
    if not validation.ok:
        state["intake_step"] = "collect"
        state["current_field"] = validation.field
        _append_assistant_message(
            state,
            validation.message or "One of the booking fields is invalid. Please try again.",
        )
        if validation.field:
            collected_data.pop(validation.field, None)
        state["collected_data"] = collected_data
        return state

    booking_result = calculate_quote(service_type, collected_data)
    state["booking_result"] = booking_result
    state["intake_step"] = "confirm"
    _append_assistant_message(
        state,
        (
            f"Your estimated {service_type} premium is ${booking_result['premium']:.2f} per year. "
            "Reply accept to confirm, adjust to change details, or restart to start over."
        ),
    )
    return state


def _append_assistant_message(state: dict, content: str) -> None:
    messages = list(state.get("messages", []))
    messages.append({"role": "assistant", "content": content})
    state["messages"] = messages

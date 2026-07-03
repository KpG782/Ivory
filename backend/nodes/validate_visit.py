from __future__ import annotations

from services.visit_estimator import estimate_visit, validate_visit_inputs

SERVICE_FLOW_LABELS = {
    "cleaning": "cleaning visit",
    "emergency": "emergency visit",
    "cosmetic": "cosmetic consultation",
}


def validate_visit(state: dict, message: str | None = None) -> dict:
    service_type = state.get("service_type")
    collected_data = dict(state.get("collected_data", {}))

    validation = validate_visit_inputs(service_type, collected_data)
    if not validation.ok:
        state["intake_step"] = "collect"
        state["current_field"] = validation.field
        _append_assistant_message(
            state,
            validation.message or "One of the intake fields is invalid. Please try again.",
        )
        if validation.field:
            collected_data.pop(validation.field, None)
        state["collected_data"] = collected_data
        return state

    visit_estimate = estimate_visit(service_type, collected_data)
    state["visit_estimate"] = visit_estimate
    state["intake_step"] = "confirm"
    service_label = SERVICE_FLOW_LABELS.get(service_type, str(service_type))
    _append_assistant_message(
        state,
        (
            f"Your estimated {service_label} cost is "
            f"${visit_estimate['estimate_low']:.2f}–${visit_estimate['estimate_high']:.2f}. "
            "This is an educational estimate, not a diagnosis or final price. "
            "Reply accept to confirm, adjust to change details, or restart to start over."
        ),
    )
    return state


def _append_assistant_message(state: dict, content: str) -> None:
    messages = list(state.get("messages", []))
    messages.append({"role": "assistant", "content": content})
    state["messages"] = messages

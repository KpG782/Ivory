from __future__ import annotations

from typing import Any


SERVICE_LABELS = {
    "emergency": ("emergency", "urgent", "broken tooth", "chipped"),
    "cosmetic": ("cosmetic", "whitening", "veneers", "aligners", "smile makeover"),
    "cleaning": ("cleaning", "checkup", "check-up", "check up", "exam", "hygiene"),
}


def identify_service(state: dict[str, Any], message: str) -> dict[str, Any]:
    state["mode"] = "transactional"
    state["intake_step"] = "identify"

    service_type = detect_service(message) or state.get("service_type")
    if not service_type:
        assistant_message = (
            "Which type of visit would you like to set up: a cleaning, "
            "an emergency visit, or a cosmetic consultation?"
        )
        state["current_field"] = None
        _append_assistant_message(state, assistant_message)
        return state

    state["service_type"] = service_type
    state["intake_step"] = "collect"
    state["current_field"] = None
    # Do not append a message here — collect_details (called immediately after in graph.py)
    # will emit the first field question, which becomes the visible response.
    return state


def detect_service(message: str | None) -> str | None:
    if not message:
        return None
    lowered = message.lower()
    for service_type, labels in SERVICE_LABELS.items():
        if any(label in lowered for label in labels):
            return service_type
    return None


def _append_assistant_message(state: dict[str, Any], content: str) -> None:
    messages = list(state.get("messages", []))
    messages.append({"role": "assistant", "content": content})
    state["messages"] = messages

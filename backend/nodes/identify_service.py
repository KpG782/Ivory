from __future__ import annotations

from typing import Any

from services.catalog import detect_service


def identify_service(state: dict[str, Any], message: str) -> dict[str, Any]:
    state["mode"] = "transactional"
    state["intake_step"] = "identify"

    service_type = detect_service(message) or state.get("service_type")
    if not service_type:
        assistant_message = (
            "Which service would you like to book: cleaning, consultation, whitening — or is this an emergency?"
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


def _append_assistant_message(state: dict[str, Any], content: str) -> None:
    messages = list(state.get("messages", []))
    messages.append({"role": "assistant", "content": content})
    state["messages"] = messages

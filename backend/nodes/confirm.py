from __future__ import annotations

from nodes.router import interpret_confirmation
from services import front_desk


def confirm(state: dict, message: str) -> dict:
    action = interpret_confirmation(message)
    visit_estimate = state.get("visit_estimate")

    if action == "accept" and not visit_estimate:
        _append_assistant_message(
            state,
            "There is no visit estimate ready to confirm yet. Please complete the intake details first.",
        )
        state["mode"] = "transactional"
        state["intake_step"] = "collect" if state.get("service_type") else "identify"
        return state

    if action == "accept":
        visit_estimate = visit_estimate or {}
        summary = visit_estimate.get("summary", "your appointment request")
        # The only place integrations ever fire: an explicit accept on a built
        # estimate. The results are rendered as a deterministic block.
        results = front_desk.process_accept(
            str(state.get("service_type") or ""),
            dict(state.get("collected_data", {})),
            dict(visit_estimate),
        )
        action_lines = "\n".join(f"- {result.name}: {result.detail}" for result in results)
        _append_assistant_message(
            state,
            (
                f"Confirmed. I have finalized {summary}.\n\n"
                f"Front desk actions:\n{action_lines}\n\n"
                "Reply restart if you want to set up another visit."
            ),
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
        state["visit_estimate"] = None
        state["mode"] = "transactional"
        state["service_type"] = service_type
        return state

    if action == "restart":
        _reset_intake_state(state)
        _append_assistant_message(
            state,
            (
                "The intake has been restarted. Which type of visit would you like "
                "to set up: a cleaning, an emergency visit, or a cosmetic consultation?"
            ),
        )
        return state

    _append_assistant_message(
        state,
        "Please reply accept, adjust, or restart so I know how to handle the appointment request.",
    )
    return state


def _reset_intake_state(state: dict) -> None:
    state["mode"] = "transactional"
    state["intake_step"] = "identify"
    state["service_type"] = None
    state["collected_data"] = {}
    state["visit_estimate"] = None
    state["pending_question"] = None
    state["current_field"] = None
    state["last_error"] = None


def _append_assistant_message(state: dict, content: str) -> None:
    messages = list(state.get("messages", []))
    messages.append({"role": "assistant", "content": content})
    state["messages"] = messages

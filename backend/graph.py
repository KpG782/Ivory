"""LangGraph orchestration for Ivory.

This is a deterministic state machine. Each user turn is a single graph
invocation that runs ``router -> handler -> END``. The router node makes one
deterministic routing decision (see ``nodes.router.decide``); the handler does
the work for that state. The AI is never on the control-flow path — it only
writes RAG answer text inside ``rag_answer``.

Durable memory comes from LangGraph's checkpointer, keyed by
``thread_id == session_id``. The checkpointer is the single source of truth for
conversation state; ``run_graph`` loads the prior checkpoint, appends the new
user message, invokes the graph, and the checkpointer atomically saves the
result. There is no separate hand-rolled session store anymore.
"""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from nodes.collect_details import collect_details, get_field_prompt
from nodes.confirm import confirm
from nodes.identify_service import detect_service, identify_service
from nodes.rag import rag_answer
from nodes.router import decide
from state import ChatState, build_initial_state, clone_state


SERVICE_FLOW_LABELS = {
    "cleaning": "cleaning visit",
    "emergency": "emergency visit",
    "cosmetic": "cosmetic consultation",
}


# ── Nodes ───────────────────────────────────────────────────────────────────

def _router_node(state: ChatState) -> ChatState:
    """Compute the deterministic route for this turn (no side effects on text)."""
    working_state = clone_state(state)
    messages = working_state.get("messages", [])
    if not messages:
        working_state["route"] = "rag"
        return working_state

    latest_message = messages[-1].get("content", "")
    route = decide(working_state, latest_message)

    # Starting an intake may also mean switching service mid-intake, which
    # requires discarding the half-collected data for the old service. This is
    # the only state mutation the router performs, and it is fully rule-driven.
    if route == "start_intake":
        _apply_service_switch(working_state, latest_message)

    working_state["route"] = route
    return working_state


def _apply_service_switch(state: ChatState, message: str) -> None:
    service = detect_service(message)
    current_type = state.get("service_type")
    mid_intake = (
        state.get("mode") == "transactional"
        and state.get("intake_step") in {"collect", "validate", "confirm"}
    )
    if service and service != current_type and mid_intake:
        _reset_intake_progress(state)
        state["service_type"] = service
        return
    # A fresh intake started from conversational mode (e.g. right after an
    # accepted visit) must not inherit the previous patient's answers or a
    # stale estimate — the new flow has to ask its own questions.
    if not mid_intake and (state.get("collected_data") or state.get("visit_estimate")):
        _reset_intake_progress(state)
        if service:
            state["service_type"] = service


def _rag_node(state: ChatState) -> ChatState:
    """Answer a question, then (if mid-intake) re-ask the paused field — a real
    resume driven by checkpointed state, not a string-append trick."""
    working_state = ChatState(**rag_answer(clone_state(state)))
    if working_state.get("mode") != "transactional":
        return working_state

    step = working_state.get("intake_step")
    if (
        step == "collect"
        and working_state.get("service_type")
        and working_state.get("current_field")
    ):
        service_type = str(working_state["service_type"])
        service_label = SERVICE_FLOW_LABELS.get(service_type, service_type)
        _append_to_last_assistant_message(
            working_state,
            f"\n\nNow, back to your {service_label} intake — "
            f"{get_field_prompt(service_type, working_state['current_field'])}",
        )
    elif step == "identify":
        # Keep this menu identical to the one in nodes/identify_service.py.
        _append_to_last_assistant_message(
            working_state,
            "\n\nWhich type of visit would you like to set up: a cleaning, "
            "an emergency visit, or a cosmetic consultation?",
        )

    return working_state


def _identify_service_node(state: ChatState) -> ChatState:
    latest_message = state.get("messages", [])[-1].get("content", "")
    return ChatState(**identify_service(clone_state(state), latest_message))


def _collect_details_node(state: ChatState) -> ChatState:
    current_field = state.get("current_field")
    latest_message = state.get("messages", [])[-1].get("content", "")
    message = latest_message if current_field else None
    return ChatState(**collect_details(clone_state(state), message))


def _validate_visit_node(state: ChatState) -> ChatState:
    from nodes.validate_visit import validate_visit

    return ChatState(**validate_visit(clone_state(state)))


def _confirm_node(state: ChatState) -> ChatState:
    latest_message = state.get("messages", [])[-1].get("content", "")
    return ChatState(**confirm(clone_state(state), latest_message))


# ── Edges ───────────────────────────────────────────────────────────────────

def _route_from_router(state: ChatState) -> Literal[
    "rag_answer",
    "identify_service",
    "collect_details",
    "confirm",
]:
    mapping = {
        "confirm": "confirm",
        "start_intake": "identify_service",
        "identify": "identify_service",
        "collect": "collect_details",
        "answer_then_resume": "rag_answer",
        "rag": "rag_answer",
    }
    return mapping.get(state.get("route", "rag"), "rag_answer")  # type: ignore[return-value]


def _route_after_identify(state: ChatState) -> Literal["collect_details", "__end__"]:
    return "collect_details" if state.get("intake_step") == "collect" else END


def _route_after_collect(state: ChatState) -> Literal["validate_visit", "__end__"]:
    return "validate_visit" if state.get("intake_step") == "validate" else END


def _route_after_confirm(state: ChatState) -> Literal["collect_details", "__end__"]:
    return "collect_details" if state.get("intake_step") == "collect" else END


def _build_graph() -> StateGraph:
    graph = StateGraph(ChatState)
    graph.add_node("router", _router_node)
    graph.add_node("rag_answer", _rag_node)
    graph.add_node("identify_service", _identify_service_node)
    graph.add_node("collect_details", _collect_details_node)
    graph.add_node("validate_visit", _validate_visit_node)
    graph.add_node("confirm", _confirm_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        _route_from_router,
        {
            "rag_answer": "rag_answer",
            "identify_service": "identify_service",
            "collect_details": "collect_details",
            "confirm": "confirm",
        },
    )
    graph.add_edge("rag_answer", END)
    graph.add_conditional_edges(
        "identify_service",
        _route_after_identify,
        {"collect_details": "collect_details", END: END},
    )
    graph.add_conditional_edges(
        "collect_details",
        _route_after_collect,
        {"validate_visit": "validate_visit", END: END},
    )
    graph.add_edge("validate_visit", END)
    graph.add_conditional_edges(
        "confirm",
        _route_after_confirm,
        {"collect_details": "collect_details", END: END},
    )

    return graph


# ── Compiled graph + durable session API ────────────────────────────────────

_checkpointer = MemorySaver()
COMPILED_GRAPH = _build_graph().compile(checkpointer=_checkpointer)
_THREAD_IDS: set[str] = set()


def _config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


def run_graph(session_id: str, message: str) -> ChatState:
    """Run one turn for *session_id*: load checkpoint, append the message, invoke.

    The checkpointer is the source of truth, so there is no manual save — the
    graph persists the new state atomically as part of ``invoke``.
    """
    config = _config(session_id)
    snapshot = COMPILED_GRAPH.get_state(config)
    base = dict(snapshot.values) if snapshot.values else dict(build_initial_state(session_id))

    base["session_id"] = session_id
    base["last_error"] = None
    base["trace_id"] = str(uuid4())
    messages = list(base.get("messages", []))
    messages.append({"role": "user", "content": message})
    base["messages"] = messages

    result = COMPILED_GRAPH.invoke(base, config)
    _THREAD_IDS.add(session_id)
    return ChatState(**dict(result))


def get_session_state(session_id: str) -> ChatState | None:
    """Read the durable state for a session straight from the checkpointer."""
    snapshot = COMPILED_GRAPH.get_state(_config(session_id))
    if not snapshot.values:
        return None
    return ChatState(**dict(snapshot.values))


def set_session_state(session_id: str, state: ChatState) -> None:
    """Overwrite the durable state for a session (used by /reset)."""
    COMPILED_GRAPH.update_state(_config(session_id), dict(state))
    _THREAD_IDS.add(session_id)


def reset_all() -> None:
    """Drop all sessions by replacing the checkpointer. Used by the test suite."""
    global COMPILED_GRAPH, _checkpointer, _THREAD_IDS
    _checkpointer = MemorySaver()
    COMPILED_GRAPH = _build_graph().compile(checkpointer=_checkpointer)
    _THREAD_IDS = set()


def session_count() -> int:
    return len(_THREAD_IDS)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _reset_intake_progress(state: ChatState) -> None:
    state["service_type"] = None
    state["collected_data"] = {}
    state["visit_estimate"] = None
    state["pending_question"] = None
    state["current_field"] = None
    state["intake_step"] = "identify"
    state["mode"] = "transactional"


def _append_to_last_assistant_message(state: ChatState, suffix: str) -> None:
    messages = list(state.get("messages", []))
    if not messages:
        return
    if messages[-1].get("role") != "assistant":
        return
    messages[-1]["content"] = f"{messages[-1].get('content', '')}{suffix}"
    state["messages"] = messages

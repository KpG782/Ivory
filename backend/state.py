from __future__ import annotations

from copy import deepcopy
from typing import Any, TypedDict
from uuid import uuid4


class ChatState(TypedDict, total=False):
    session_id: str
    messages: list[dict[str, str]]
    mode: str
    intent: str
    quote_step: str
    insurance_type: str | None
    collected_data: dict[str, Any]
    quote_result: dict[str, Any] | None
    pending_question: str | None
    last_error: str | None
    trace_id: str | None
    current_field: str | None
    # Transient: the deterministic route chosen for the current turn. Written by
    # the router node, read by the conditional edge. Persisted but recomputed
    # every turn, so its stored value is never trusted across turns.
    route: str


def build_initial_state(session_id: str) -> ChatState:
    return ChatState(
        session_id=session_id,
        messages=[],
        mode="conversational",
        intent="question",
        quote_step="identify",
        insurance_type=None,
        collected_data={},
        quote_result=None,
        pending_question=None,
        last_error=None,
        trace_id=str(uuid4()),
        current_field=None,
        route="rag",
    )


def clone_state(state: ChatState) -> ChatState:
    copied = deepcopy(dict(state))
    return ChatState(**copied)

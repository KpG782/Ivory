"""Deterministic conversation router.

The single rule of this system: **the AI never decides control flow.** This
module turns (state, message) into exactly one route per turn using a fixed,
ordered set of rules. There is no LLM call and no probabilistic guessing here,
so the same inputs always produce the same route — it is testable and
defensible.

The LLM is still used elsewhere (to write RAG answer text); it is simply never
allowed to steer the conversation.

Route labels returned by ``decide``:

- ``"confirm"``            — accept / adjust / restart an existing visit estimate
- ``"start_intake"``       — begin a new intake or switch service
- ``"identify"``           — user is choosing which visit type to set up
- ``"collect"``            — user gave a field value (validate + store)
- ``"answer_then_resume"`` — user paused mid-intake to ask a question
- ``"rag"``                — answer a knowledge-base question
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from nodes.identify_service import detect_service

# Deterministic keyword signals. These are the only words the router reads.
# Matching is whole-word: "book" must not fire inside "Booker" or "facebook",
# and "yes" must not fire inside "yesterday".
RESTART_HINTS = ("restart", "start over", "reset")
ADJUST_HINTS = ("adjust", "change", "modify", "update", "edit")
AFFIRM_HINTS = ("yes", "accept", "confirm", "looks good", "approve", "ok", "okay", "good")
PROGRESSION_HINTS = ("next", "continue", "go on", "proceed")
# Explicit booking words that start (or switch) an intake from any state.
BOOKING_HINTS = (
    "book",
    "booking",
    "booked",
    "appointment",
    "appointments",
    "schedule",
    "scheduling",
    "reschedule",
)
# Explicit visit intent that may appear without a literal booking word.
INTAKE_INTENT_HINTS = (
    "price",
    "pricing",
    "cost",
    "costs",
    "estimate",
    "come in",
    "set up a visit",
    "sign up",
)
# A confirm-step reply containing any of these is a rejection, never an accept
# ("no, this is not ok" must not book the appointment).
NEGATION_TOKENS = {
    "no",
    "not",
    "dont",
    "don't",
    "isnt",
    "isn't",
    "nope",
    "nah",
    "never",
    "cancel",
    "wrong",
    "incorrect",
}

ACTIVE_INTAKE_STEPS = {"collect", "validate", "confirm"}


def decide(state: dict[str, Any], message: str) -> str:
    """Return the route for this turn. Pure function of (state, message)."""
    text = message.strip().lower()
    mode = state.get("mode", "conversational")
    step = state.get("intake_step", "identify")
    current_field = state.get("current_field")

    # P1 — An explicit restart while inside an intake always wins.
    if mode == "transactional" and _contains_any(text, RESTART_HINTS):
        return "confirm"

    # P2 — A mid-intake question is ALWAYS answered-then-resumed, even when it
    #      mentions a booking word ("How much does a whitening appointment
    #      cost?" must never wipe collected data or switch the service).
    if current_field and "?" in text:
        return "answer_then_resume"

    # P3 — An explicit non-question booking request starts an intake or
    #      switches service. This is how a mid-intake service switch happens.
    if _contains_any(text, BOOKING_HINTS):
        return "start_intake"

    # P4 — We are waiting for one specific field value (the core invariant).
    #      Anything non-question is handed to collect_details, which itself
    #      tries to validate-and-store first and re-prompts on failure.
    if current_field:
        return "collect"

    # P5 — A visit estimate is built and waiting for accept / adjust / restart.
    if mode == "transactional" and step == "confirm":
        return "confirm"

    # P6 — We asked which visit type to set up. A service word (or a simple
    #      affirmation) selects it; anything else is a real question.
    if mode == "transactional" and step == "identify":
        if detect_service(text) or _contains_any(text, AFFIRM_HINTS + PROGRESSION_HINTS):
            return "identify"
        return "rag"

    # P7 — Idle/conversational. Only an explicit, non-question visit intent
    #      starts an intake; everything else is a knowledge question.
    if "?" not in text and _contains_any(text, INTAKE_INTENT_HINTS):
        return "start_intake"
    return "rag"


def interpret_confirmation(message: str) -> str | None:
    """Map a confirm-step reply to accept / adjust / restart, deterministically."""
    lowered = message.strip().lower()
    if _contains_any(lowered, RESTART_HINTS):
        return "restart"
    if _contains_any(lowered, ADJUST_HINTS):
        return "adjust"
    # A negated reply ("no, this is not ok") must never be read as an accept —
    # accept is the one action with external side effects.
    tokens = set(re.findall(r"[a-z']+", lowered))
    if tokens & NEGATION_TOKENS:
        return None
    if _contains_any(lowered, AFFIRM_HINTS):
        return "accept"
    return None


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    return any(
        re.search(rf"\b{re.escape(needle)}\b", text) is not None for needle in needles
    )

"""Deterministic conversation router.

The single rule of this system: **the AI never decides control flow.** This
module turns (state, message) into exactly one route per turn using a fixed,
ordered set of rules. There is no LLM call and no probabilistic guessing here,
so the same inputs always produce the same route — it is testable and
defensible.

The LLM is still used elsewhere (to write RAG answer text); it is simply never
allowed to steer the conversation.

Route labels returned by ``decide``:

- ``"confirm"``            — accept / adjust / restart an existing intake
- ``"start_intake"``       — begin a new appointment intake or switch service
- ``"identify"``           — user is choosing which dental service to book
- ``"collect"``            — user gave a field value (validate + store)
- ``"answer_then_resume"`` — user paused mid-intake to ask a question
- ``"rag"``                — answer a knowledge-base question

Rule ordering (P1–P6):
  P1  Explicit restart while inside an intake.
  P2  Explicit booking/appointment request from any state.
  P3  A field is pending (current_field is set).
  P3b Already booked + affirmation without "?" → re-emit success via confirm.
  P4  Intake built and waiting for accept / adjust / restart.
  P5  Identifying which service to book.
  P6  Idle/conversational fallback.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from services.catalog import detect_service

# Deterministic keyword signals. These are the only words the router reads.
# All hint tuples are matched with word-boundary (\b) anchoring, consistent
# with services/catalog.py detect_service — partial-word hits (e.g. "booking"
# containing "book", "unavailable" containing "available") are not matched.
RESTART_HINTS = ("restart", "start over", "reset")
ADJUST_HINTS = ("adjust", "change", "modify", "update", "edit")
AFFIRM_HINTS = ("yes", "accept", "confirm", "looks good", "approve", "ok", "okay", "good")
PROGRESSION_HINTS = ("next", "continue", "go on", "proceed")
# Explicit booking intent that may appear without the literal booking words.
# Word-boundary matching requires listing inflections we want to catch, so both
# "book" and "booking" (and "appointment" / "appointments") are included.
BOOKING_INTENT_HINTS = ("price", "pricing", "availability", "available", "come in", "see the dentist", "slot", "walk in")

ACTIVE_INTAKE_STEPS = {"collect", "validate", "confirm"}


def decide(state: dict[str, Any], message: str) -> str:
    """Return the route for this turn. Pure function of (state, message)."""
    text = message.strip().lower()
    mode = state.get("mode", "conversational")
    step = state.get("intake_step", "identify")
    current_field = state.get("current_field")

    # P1 — An explicit restart while inside an intake, OR after booking is
    #      complete, always wins. The success message advertises "restart" as
    #      the CTA, so we must honour it even though mode has returned to
    #      "conversational" at the terminal "booked" step.
    if (mode == "transactional" or step == "booked") and _contains_any(text, RESTART_HINTS):
        return "confirm"

    # P2 — An explicit booking/appointment request starts an intake or switches
    #      service, from any state. This is how a mid-intake service switch is
    #      handled.
    if _contains_any(text, ("appointment", "appointments", "book", "booking", "schedule")):
        return "start_intake"

    # P3 — We are waiting for one specific field value (the core invariant).
    #      A literal "?" is the only signal that the user paused to ask a
    #      question. Anything else is handed to collect_details, which itself
    #      tries to validate-and-store first and re-prompts on failure.
    if current_field:
        if "?" in text:
            return "answer_then_resume"
        return "collect"

    # P3b — Booking is already confirmed ("booked") and the user sends a plain
    #       affirmation or adjust signal (no "?"). Route to confirm so it can
    #       detect intake_step == "booked" and respond appropriately — the
    #       accept branch short-circuits via book_appointment's idempotency
    #       guard, the adjust branch emits the "already booked" nudge.
    if step == "booked" and _contains_any(text, AFFIRM_HINTS + ADJUST_HINTS) and "?" not in text:
        return "confirm"

    # P4 — An intake is built and waiting for accept / adjust / restart.
    if mode == "transactional" and step == "confirm":
        return "confirm"

    # P5 — We asked which service to book. A service word (or a simple
    #      affirmation) selects it; anything else is a real question.
    if mode == "transactional" and step == "identify":
        if detect_service(text) or _contains_any(text, AFFIRM_HINTS + PROGRESSION_HINTS):
            return "identify"
        return "rag"

    # P6 — Idle/conversational. Only an explicit, non-question booking intent
    #      (or a detected dental service keyword) starts an intake; everything
    #      else is a knowledge question.
    #      The "?" guard is essential: "Does whitening damage enamel?" contains
    #      a service keyword but must stay rag.
    if "?" not in text and (_contains_any(text, BOOKING_INTENT_HINTS) or detect_service(text)):
        return "start_intake"
    return "rag"


def interpret_confirmation(message: str) -> str | None:
    """Map a confirm-step reply to accept / adjust / restart, deterministically."""
    lowered = message.strip().lower()
    if _contains_any(lowered, RESTART_HINTS):
        return "restart"
    if _contains_any(lowered, ADJUST_HINTS):
        return "adjust"
    if _contains_any(lowered, AFFIRM_HINTS):
        return "accept"
    return None


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    """Return True if any needle appears as a whole word in text.

    Uses word-boundary (\\b) anchoring so that, e.g., "book" does not fire
    inside "facebook", and "available" does not fire inside "unavailable".
    Matches are case-insensitive because callers always pass lowercased text.
    """
    return any(re.search(rf"\b{re.escape(needle)}\b", text) for needle in needles)

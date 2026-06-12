"""Service catalog for dental bookings.

The catalog is the single source of truth for bookable services. Router keywords,
intake prompts, and Cal.com event types all derive from this definition.
"""

import re
from typing import Any

SERVICES: dict[str, dict[str, Any]] = {
    "cleaning": {
        "label": "Cleaning & checkup",
        "duration_min": 45,
        "cal_event_type": "cleaning-45",
    },
    "consultation": {
        "label": "Consultation",
        "duration_min": 30,
        "cal_event_type": "consult-30",
    },
    "whitening": {
        "label": "Whitening",
        "duration_min": 60,
        "cal_event_type": "whitening-60",
    },
    "emergency": {
        "label": "Emergency visit",
        "duration_min": 30,
        "cal_event_type": "emergency-30",
    },
}

_KEYWORDS = {
    # Intentional ordering (top-down, first match wins):
    #   1. emergency — must be checked first so an urgent message is never
    #      downgraded to a lower-priority service even when other keywords
    #      co-occur (e.g. "chipped tooth whitening" → emergency).
    #   2. consultation — before cleaning so "checkup consult" resolves to
    #      consultation while a bare "checkup" still falls through to cleaning.
    #   3. cleaning — catch-all for routine hygiene / checkup phrasing.
    #   4. whitening — cosmetic; lowest priority, no overlap with urgent terms.
    "emergency": (
        "emergency",
        "toothache",
        "tooth ache",
        "killing me",
        "knocked out",
        "broken tooth",
        "chipped",
        "swelling",
        "bleeding gums",
        "severe pain",
    ),
    "consultation": (
        "consultation",
        "consult",
        "second opinion",
        "new patient exam",
    ),
    "cleaning": (
        "cleaning",
        "clean my teeth",
        "checkup",
        "check-up",
        "hygiene",
    ),
    "whitening": (
        "whitening",
        "whiten",
        "bleaching",
    ),
}


def detect_service(text: str) -> str | None:
    """Detect the service type from user input text.

    Performs top-down word-boundary keyword matching against the service
    catalog.  Returns the first matching service key or None if no match.

    Word boundaries (\b) prevent partial-word false positives, e.g.
    "consult" will not match "consulting" or "consultant".
    """
    lowered = text.lower()
    for service, needles in _KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(needle)}\b", lowered) for needle in needles):
            return service
    return None

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from services.catalog import SERVICES

# ---------------------------------------------------------------------------
# Dental intake field definitions
# ---------------------------------------------------------------------------

INTAKE_FIELDS = [
    {"name": "patient_name",   "prompt": "May I have your full name?",                                              "type": "str",   "min_length": 2},
    {"name": "phone",          "prompt": "What's the best phone number to reach you?",                              "type": "phone"},
    {"name": "email",          "prompt": "And your email for the confirmation?",                                    "type": "email"},
    {"name": "patient_status", "prompt": "Are you a new or returning patient?",                                     "type": "str",   "allowed": ["new", "returning"]},
    {"name": "preferred_slot", "prompt": "What day and time work best? (e.g. 'Wednesday 2:30 PM')",                 "type": "slot"},
]

# One shared schema for all services — keeps the per-service lookup code working.
FIELD_SPECS: dict[str, list[dict[str, Any]]] = {s: INTAKE_FIELDS for s in SERVICES}

# ---------------------------------------------------------------------------
# Slot parsing
# ---------------------------------------------------------------------------

_WEEKDAY_NAMES: dict[str, int] = {
    "monday": 0,    "mon": 0,
    "tuesday": 1,   "tue": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3,  "thu": 3,
    "friday": 4,    "fri": 4,
    "saturday": 5,  "sat": 5,
    "sunday": 6,    "sun": 6,
}

_SLOT_PATTERN = re.compile(
    r"\b(?P<day>monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|mon|tue|wed|thu|fri|sat|sun)\b"
    r"[\s,]+(?:at\s+)?(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<ampm>am|pm)\b",
    re.IGNORECASE,
)


def parse_slot_phrase(value: str) -> datetime | None:
    """Parse a natural-language slot phrase into the next strictly-future UTC datetime.

    Accepts formats like "Wednesday 2:30 PM" or "wed 2pm" (weekday + hour[:minute] am/pm).
    Returns a timezone-aware UTC datetime, or None if the phrase cannot be parsed.

    The returned datetime is the next occurrence of that weekday/time that is strictly
    in the future (UTC). If the requested weekday is today but the time has already
    passed, the next-week occurrence is returned instead.
    """
    m = _SLOT_PATTERN.search(value.strip())
    if not m:
        return None

    day_str = m.group("day").lower()
    raw_hour = int(m.group("hour"))
    minute = int(m.group("minute")) if m.group("minute") else 0
    ampm = m.group("ampm").lower()

    # Validate raw values before 24-hour conversion to avoid leaking
    # Python's "hour must be in 0..23" ValueError to the user.
    if not (1 <= raw_hour <= 12):
        return None
    if not (0 <= minute <= 59):
        return None

    # Convert to 24-hour
    hour = raw_hour
    if ampm == "am":
        if hour == 12:
            hour = 0
    else:  # pm
        if hour != 12:
            hour += 12

    target_weekday = _WEEKDAY_NAMES[day_str]

    now_utc = datetime.now(UTC)
    today_weekday = now_utc.weekday()

    # Days until the next occurrence of target_weekday
    days_ahead = (target_weekday - today_weekday) % 7

    # Build a candidate datetime on that date at the given time (UTC-naive for arithmetic,
    # then we attach UTC)
    candidate_date = (now_utc + timedelta(days=days_ahead)).date()
    candidate = datetime(
        candidate_date.year,
        candidate_date.month,
        candidate_date.day,
        hour,
        minute,
        0,
        tzinfo=UTC,
    )

    # Must be strictly future; if same-day and time already passed, push one week ahead.
    if candidate <= now_utc:
        candidate += timedelta(weeks=1)

    return candidate


# ---------------------------------------------------------------------------
# Public node
# ---------------------------------------------------------------------------


def collect_details(state: dict[str, Any], message: str | None = None) -> dict[str, Any]:
    service_type = state.get("service_type")
    if service_type not in FIELD_SPECS:
        _append_assistant_message(
            state,
            "I still need to know which service you'd like to book before collecting your details.",
        )
        state["intake_step"] = "identify"
        return state

    fields = FIELD_SPECS[service_type]
    collected = dict(state.get("collected_data", {}))
    current_field = state.get("current_field") or _next_missing_field(fields, collected)

    if current_field and message and message.strip():
        try:
            field_spec = _get_field_spec(fields, current_field)
            if current_field not in collected:
                collected[current_field] = _coerce_value(
                    current_field,
                    field_spec.get("type", "str"),
                    message,
                    allowed=field_spec.get("allowed"),
                    min_value=field_spec.get("min_value"),
                    max_value=field_spec.get("max_value"),
                    min_length=field_spec.get("min_length"),
                )
            state["collected_data"] = collected
        except ValueError as exc:
            prompt = _field_prompt(fields, current_field)
            _append_assistant_message(state, f"{exc} {prompt}")
            state["current_field"] = current_field
            state["intake_step"] = "collect"
            return state

    next_field = _next_missing_field(fields, collected)
    state["collected_data"] = collected
    state["mode"] = "transactional"
    if next_field:
        state["current_field"] = next_field
        state["intake_step"] = "collect"
        _append_assistant_message(state, _field_prompt(fields, next_field))
        return state

    state["current_field"] = None
    state["intake_step"] = "validate"
    return state


def get_field_prompt(service_type: str, field_name: str) -> str:
    fields = FIELD_SPECS.get(service_type, [])
    return _field_prompt(fields, field_name)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _next_missing_field(fields: list[dict[str, Any]], collected: dict[str, Any]) -> str | None:
    for field in fields:
        if field["name"] not in collected:
            return str(field["name"])
    return None


def _get_field_spec(fields: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for field in fields:
        if field["name"] == name:
            return field
    return {}


def _field_prompt(fields: list[dict[str, Any]], name: str) -> str:
    prompt = _get_field_spec(fields, name).get("prompt")
    return str(prompt) if prompt else "Please provide the next required detail."


def _coerce_value(
    field_name: str,
    field_type: str,
    raw: str,
    *,
    allowed: list[Any] | None = None,
    min_value: float | int | None = None,
    max_value: float | int | None = None,
    min_length: int | None = None,
) -> Any:
    value = raw.strip()
    if not value:
        raise ValueError("That answer was empty.")

    coerced: Any

    if field_type == "phone":
        digits = re.sub(r"\D", "", value)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError(
                "That phone number doesn't look complete — please include the area code."
            )
        return digits

    elif field_type == "email":
        stripped = value.lower().strip()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", stripped):
            raise ValueError(
                "That email doesn't look right — could you re-type it? (e.g. maria@example.com)"
            )
        return stripped

    elif field_type == "slot":
        parsed = parse_slot_phrase(value)
        if parsed is None:
            raise ValueError(
                "I couldn't read that time — try something like 'Wednesday 2:30 PM'."
            )
        now_utc = datetime.now(UTC)
        # Defensive check — parse_slot_phrase already guarantees strictly future,
        # but guard anyway in case of clock skew.
        if parsed <= now_utc:
            raise ValueError(
                "That time is in the past — what's the next day and time that works?"
            )
        # v1: store as UTC-naive isoformat (real timezone handling is a Phase 4
        # concern when Cal.com integration lands).
        return parsed.replace(tzinfo=None).isoformat()

    elif field_type == "int":
        try:
            coerced = int(value)
        except ValueError:
            raise ValueError("Please enter a whole number.")
        if min_value is not None and coerced < min_value:
            raise ValueError(_range_error_message(field_name, min_value=min_value, max_value=max_value))
        if max_value is not None and coerced > max_value:
            raise ValueError(_range_error_message(field_name, min_value=min_value, max_value=max_value))

    elif field_type == "float":
        try:
            coerced = float(value.replace(",", "").replace("$", ""))
        except ValueError:
            raise ValueError("Please enter a numeric amount.")
        if min_value is not None and coerced < float(min_value):
            raise ValueError(_range_error_message(field_name, min_value=min_value, max_value=max_value))
        if max_value is not None and coerced > float(max_value):
            raise ValueError(_range_error_message(field_name, min_value=min_value, max_value=max_value))

    elif field_type == "bool":
        lowered = value.lower()
        if lowered in {"yes", "y", "true", "1"}:
            coerced = True
        elif lowered in {"no", "n", "false", "0"}:
            coerced = False
        else:
            raise ValueError("Please reply yes or no.")

    else:
        coerced = _clean_text_value(field_name, value, min_length=min_length)

    if allowed is not None:
        if isinstance(coerced, str):
            lowered_coerced = coerced.lower()
            for option in allowed:
                if isinstance(option, str) and lowered_coerced == option.lower():
                    return option
        elif coerced in allowed:
            return coerced
        allowed_str = ", ".join(str(a) for a in allowed)
        raise ValueError(f"Please choose one of: {allowed_str}.")

    return coerced


def _clean_text_value(field_name: str, value: str, *, min_length: int | None = None) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    token_matches = re.findall(r"[a-zA-Z0-9]+", normalized)
    alpha_tokens = [token for token in token_matches if re.search(r"[A-Za-z]", token)]

    if not token_matches or not alpha_tokens:
        raise ValueError("Please enter a text value.")

    if normalized.endswith("?"):
        raise ValueError("Please answer with the requested detail only.")

    lowered = normalized.lower()
    # Dental non-answer guard: reject inputs that are obviously a booking
    # request or irrelevant topic rather than the requested field value.
    # Use word-boundary matching (consistent with router.py / services/catalog.py)
    # to avoid false positives on names like "Robin Booker" or "Maria Bookington".
    if any(
        re.search(rf"\b{re.escape(term)}\b", lowered)
        for term in ("appointment", "booking", "insurance")
    ):
        raise ValueError("Please enter the requested detail, not a new booking question.")

    if len(alpha_tokens) > 6:
        raise ValueError("Please keep the answer short and limited to the requested detail.")

    if min_length is not None and len(normalized) < min_length:
        raise ValueError("Please enter a valid text value.")

    return normalized


def _range_error_message(
    field_name: str,
    *,
    min_value: float | int | None,
    max_value: float | int | None,
) -> str:
    if min_value is not None and max_value is not None:
        return f"Please enter a number between {int(min_value)} and {int(max_value)}."
    if min_value is not None:
        return f"Please enter a number greater than or equal to {int(min_value)}."
    if max_value is not None:
        return f"Please enter a number less than or equal to {int(max_value)}."
    return "Please enter a valid number."


def _append_assistant_message(state: dict[str, Any], content: str) -> None:
    messages = list(state.get("messages", []))
    messages.append({"role": "assistant", "content": content})
    state["messages"] = messages

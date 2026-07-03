from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

CURRENT_YEAR = datetime.now(UTC).year
NAME_DENYLIST = {
    "zoo",
    "dog",
    "dogs",
    "cat",
    "cats",
    "apple",
    "banana",
}
# Domain words that signal the user asked a new clinic question instead of
# answering the free-text field they were prompted for.
TEXT_DOMAIN_BLOCKLIST = (
    "appointment",
    "booking",
    "estimate",
    "cleaning",
    "whitening",
    "dentist",
    "dental",
    "tooth",
    "teeth",
    "cost",
    "price",
)
# Multi-word or synonym answers that normalize to a canonical enum value.
ENUM_SYNONYMS = {
    "self pay": "self_pay",
    "self-pay": "self_pay",
    "cash": "self_pay",
    "out of pocket": "self_pay",
    "paying out of pocket": "self_pay",
}

_EMAIL_TOKEN_RE = r"[^@\s,]+@[^@\s,]+\.[^@\s,]+"
_YEAR_RE = r"\b(19\d{2}|20\d{2})\b"
_TIME_RE = r"\b(morning|afternoon|evening)\b"
_STATUS_RE = r"\b(insured|self[- ]?pay|cash|out of pocket)\b"

FIELD_SPECS: dict[str, list[dict[str, Any]]] = {
    "cleaning": [
        {
            "name": "patient_name",
            "prompt": "What's the patient's full name? (e.g. Maria Santos)",
            "type": "str",
            "min_length": 2,
        },
        {
            "name": "contact_email",
            "prompt": "What email should we use for confirmations? (e.g. maria@example.com)",
            "type": "email",
        },
        {
            "name": "last_visit_year",
            "prompt": "What year was your last dental visit? (e.g. 2024)",
            "type": "int",
            "min_value": 1901,
            "max_value": CURRENT_YEAR,
        },
        {
            "name": "insurance_status",
            "prompt": "Do you have dental insurance, or are you paying out of pocket? (insured or self-pay)",
            "type": "str",
            "allowed": ["insured", "self_pay"],
        },
        {
            "name": "preferred_time",
            "prompt": "What time of day works best: morning, afternoon, or evening?",
            "type": "str",
            "allowed": ["morning", "afternoon", "evening"],
        },
    ],
    "emergency": [
        {
            "name": "patient_name",
            "prompt": "What's the patient's full name? (e.g. Maria Santos)",
            "type": "str",
            "min_length": 2,
        },
        {
            "name": "contact_phone",
            "prompt": "What phone number can we reach you at? (e.g. 555-201-7788)",
            "type": "phone",
        },
        {
            "name": "issue_type",
            "prompt": "What's the problem: a toothache, chipped tooth, swelling, or a lost filling?",
            "type": "str",
            "allowed": ["toothache", "chipped_tooth", "swelling", "lost_filling"],
        },
        {
            "name": "pain_level",
            "prompt": "On a scale of 0 to 10, how bad is the pain right now?",
            "type": "int",
            "min_value": 0,
            "max_value": 10,
        },
        {
            "name": "insurance_status",
            "prompt": "Do you have dental insurance, or are you paying out of pocket? (insured or self-pay)",
            "type": "str",
            "allowed": ["insured", "self_pay"],
        },
    ],
    "cosmetic": [
        {
            "name": "patient_name",
            "prompt": "What's the patient's full name? (e.g. Maria Santos)",
            "type": "str",
            "min_length": 2,
        },
        {
            "name": "contact_email",
            "prompt": "What email should we use for confirmations? (e.g. maria@example.com)",
            "type": "email",
        },
        {
            "name": "treatment",
            "prompt": "Which treatment are you interested in: whitening, veneers, aligners, or bonding?",
            "type": "str",
            "allowed": ["whitening", "veneers", "aligners", "bonding"],
        },
        {
            "name": "budget_band",
            "prompt": "Which budget band fits best: basic, standard, or premium?",
            "type": "str",
            "allowed": ["basic", "standard", "premium"],
        },
        {
            "name": "timeline",
            "prompt": "When would you like to start: asap, this month, or flexible?",
            "type": "str",
            "allowed": ["asap", "this_month", "flexible"],
        },
    ],
}


def collect_details(state: dict[str, Any], message: str | None = None) -> dict[str, Any]:
    service_type = state.get("service_type")
    if service_type not in FIELD_SPECS:
        _append_assistant_message(
            state,
            "I still need to know the visit type before collecting intake details.",
        )
        state["intake_step"] = "identify"
        return state

    fields = FIELD_SPECS[service_type]
    collected = dict(state.get("collected_data", {}))
    current_field = state.get("current_field") or _next_missing_field(fields, collected)

    if current_field and message and message.strip():
        try:
            if service_type == "cleaning":
                collected = _merge_cleaning_multi_field_input(collected, current_field, message)
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


def _merge_cleaning_multi_field_input(
    collected: dict[str, Any],
    current_field: str,
    raw: str,
) -> dict[str, Any]:
    next_collected = dict(collected)
    lowered = raw.lower()
    compact = re.sub(r"\s+", " ", raw).strip()
    fields = FIELD_SPECS["cleaning"]

    parsed_sequential = _merge_cleaning_sequential_input(fields, next_collected, current_field, raw)
    if parsed_sequential is not None:
        next_collected = parsed_sequential

    email_match = re.search(_EMAIL_TOKEN_RE, compact)
    year_match = re.search(_YEAR_RE, compact)
    status_value = _find_insurance_status(lowered)
    time_match = re.search(_TIME_RE, lowered)

    if current_field == "patient_name":
        if email_match:
            next_collected.setdefault("contact_email", email_match.group(0))
        if year_match:
            next_collected.setdefault("last_visit_year", int(year_match.group(1)))
        if status_value:
            next_collected.setdefault("insurance_status", status_value)
        if time_match:
            next_collected.setdefault("preferred_time", time_match.group(1))

        if email_match or year_match or status_value or time_match:
            remainder = compact
            for pattern in (_EMAIL_TOKEN_RE, _YEAR_RE, _TIME_RE, _STATUS_RE):
                remainder = re.sub(pattern, "", remainder, flags=re.IGNORECASE)
            remainder = re.sub(r"[,\s]+", " ", remainder).strip(" ,")
            if remainder:
                try:
                    next_collected.setdefault(
                        "patient_name",
                        _clean_text_value("patient_name", remainder, min_length=2),
                    )
                except ValueError:
                    pass

    elif current_field == "contact_email":
        if email_match:
            next_collected.setdefault("contact_email", email_match.group(0))
        if year_match:
            next_collected.setdefault("last_visit_year", int(year_match.group(1)))
        if status_value:
            next_collected.setdefault("insurance_status", status_value)
        if time_match:
            next_collected.setdefault("preferred_time", time_match.group(1))

    elif current_field == "last_visit_year":
        if year_match:
            next_collected.setdefault("last_visit_year", int(year_match.group(1)))
        if status_value:
            next_collected.setdefault("insurance_status", status_value)
        if time_match:
            next_collected.setdefault("preferred_time", time_match.group(1))

    elif current_field == "insurance_status":
        if status_value:
            next_collected.setdefault("insurance_status", status_value)
        if time_match:
            next_collected.setdefault("preferred_time", time_match.group(1))

    elif current_field == "preferred_time":
        if time_match:
            next_collected.setdefault("preferred_time", time_match.group(1))

    return next_collected


def _merge_cleaning_sequential_input(
    fields: list[dict[str, Any]],
    collected: dict[str, Any],
    current_field: str,
    raw: str,
) -> dict[str, Any] | None:
    if "," not in raw:
        return None

    field_names = [str(field["name"]) for field in fields]
    if current_field not in field_names:
        return None

    parts = [
        re.sub(r"^[`'\"\s]+|[`'\"\s]+$", "", part)
        for part in raw.split(",")
    ]
    parts = [part for part in parts if part]
    if len(parts) < 2:
        return None

    next_collected = dict(collected)
    start_index = field_names.index(current_field)

    for field_name, raw_value in zip(field_names[start_index:], parts, strict=False):
        if field_name in next_collected:
            continue
        field_spec = _get_field_spec(fields, field_name)
        try:
            next_collected[field_name] = _coerce_value(
                field_name,
                str(field_spec.get("type", "str")),
                raw_value,
                allowed=field_spec.get("allowed"),
                min_value=field_spec.get("min_value"),
                max_value=field_spec.get("max_value"),
                min_length=field_spec.get("min_length"),
            )
        except ValueError:
            break

    return next_collected


def _find_insurance_status(lowered: str) -> str | None:
    if re.search(r"\binsured\b", lowered):
        return "insured"
    if re.search(r"\b(self[- ]?pay|cash|out of pocket)\b", lowered):
        return "self_pay"
    return None


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


def _field_type(fields: list[dict[str, Any]], name: str) -> str:
    return str(_get_field_spec(fields, name).get("type", "str"))


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
    if field_type == "int":
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
    elif field_type == "email":
        candidate = value.strip().rstrip(".,;")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", candidate):
            raise ValueError("Please enter a valid email address, for example maria@example.com.")
        coerced = candidate
    elif field_type == "phone":
        digits = re.sub(r"\D", "", value)
        if len(digits) < 7:
            raise ValueError("Please enter a phone number with at least 7 digits.")
        coerced = re.sub(r"\s+", " ", value).strip()
    else:
        if allowed is not None:
            coerced = _normalize_enum_value(value)
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


def _normalize_enum_value(value: str) -> str:
    """Normalize an enum answer: drop articles, map synonyms, canonical snake_case."""
    lowered = re.sub(r"\s+", " ", value).strip().lower().strip(".,!")
    for article in ("a ", "an ", "the "):
        if lowered.startswith(article):
            lowered = lowered[len(article):]
            break
    canonical = ENUM_SYNONYMS.get(lowered, lowered)
    return canonical.replace("-", "_").replace(" ", "_")


def _clean_text_value(field_name: str, value: str, *, min_length: int | None = None) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    token_matches = re.findall(r"[a-zA-Z0-9]+", normalized)
    alpha_tokens = [token for token in token_matches if re.search(r"[A-Za-z]", token)]

    if not token_matches or not alpha_tokens:
        raise ValueError("Please enter a text value.")

    if normalized.endswith("?"):
        raise ValueError("Please answer with the requested detail only.")

    lowered = normalized.lower()
    if any(term in lowered for term in TEXT_DOMAIN_BLOCKLIST):
        raise ValueError("Please enter the requested detail, not a new appointment question.")

    if len(alpha_tokens) > 6:
        raise ValueError("Please keep the answer short and limited to the requested detail.")

    if min_length is not None and len(normalized) < min_length:
        raise ValueError("Please enter a valid text value.")

    if field_name == "patient_name":
        if lowered.startswith(("i ", "my ", "we ", "they ", "hello", "hi ")):
            raise ValueError("Please enter only the patient's full name.")
        lower_tokens = {token.lower() for token in alpha_tokens}
        if {"like", "love"} & lower_tokens:
            raise ValueError("Please enter a real patient name.")
        if lower_tokens & NAME_DENYLIST:
            raise ValueError("Please enter a real patient name, for example Maria Santos.")
        if len(alpha_tokens) < 2:
            raise ValueError("Please enter the patient's full name, for example Maria Santos.")
        if len(alpha_tokens) > 4:
            raise ValueError("Please enter only the patient's full name.")
        if not re.fullmatch(r"[A-Za-z\s,.'-]+", normalized):
            raise ValueError("Please enter a valid patient name.")

    return normalized


def _range_error_message(
    field_name: str,
    *,
    min_value: float | int | None,
    max_value: float | int | None,
) -> str:
    if field_name == "last_visit_year" and min_value is not None and max_value is not None:
        return f"Last dental visit year must be between {int(min_value)} and {int(max_value)}."
    if field_name == "pain_level" and min_value is not None and max_value is not None:
        return (
            "Please enter a pain level between "
            f"{int(min_value)} and {int(max_value)}."
        )
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

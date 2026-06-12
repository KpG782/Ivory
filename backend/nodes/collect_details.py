from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

CURRENT_YEAR = datetime.now(UTC).year
LOCATION_DENYLIST = {
    "zoo",
    "dog",
    "dogs",
    "cat",
    "cats",
    "apple",
    "banana",
}

FIELD_SPECS: dict[str, list[dict[str, Any]]] = {
    "auto": [
        {
            "name": "vehicle_year",
            "prompt": "What year is the vehicle? (e.g. 2019)",
            "type": "int",
            "min_value": 1901,
            "max_value": CURRENT_YEAR,
        },
        {"name": "vehicle_make", "prompt": "What is the vehicle make? (e.g. Toyota)", "type": "str", "min_length": 2},
        {"name": "vehicle_model", "prompt": "What is the vehicle model? (e.g. Camry)", "type": "str", "min_length": 2},
        {"name": "driver_age", "prompt": "How old is the primary driver?", "type": "int", "min_value": 16, "max_value": 120},
        {
            "name": "accidents_last_5yr",
            "prompt": "How many accidents has the driver had in the last 5 years?",
            "type": "int",
            "min_value": 0,
            "max_value": 10,
        },
        {
            "name": "coverage_level",
            "prompt": "Which coverage level do you want: basic, standard, or comprehensive?",
            "type": "str",
            "allowed": ["basic", "standard", "comprehensive"],
        },
    ],
    "home": [
        {
            "name": "property_type",
            "prompt": "Is the property a house, condo, or apartment?",
            "type": "str",
            "allowed": ["house", "condo", "apartment"],
        },
        {
            "name": "location",
            "prompt": "Which city or location is the property in?",
            "type": "str",
            "min_length": 2,
        },
        {
            "name": "estimated_value",
            "prompt": "What is the estimated property value in USD? (e.g. 350000)",
            "type": "float",
            "min_value": 10000,
        },
        {
            "name": "year_built",
            "prompt": "What year was the property built?",
            "type": "int",
            "min_value": 1801,
            "max_value": CURRENT_YEAR,
        },
        {
            "name": "coverage_level",
            "prompt": "Which coverage level do you want: basic, standard, or comprehensive?",
            "type": "str",
            "allowed": ["basic", "standard", "comprehensive"],
        },
    ],
    "life": [
        {"name": "age", "prompt": "How old is the insured person?", "type": "int", "min_value": 18, "max_value": 85},
        {
            "name": "health_status",
            "prompt": "How would you describe health status: excellent, good, fair, or poor?",
            "type": "str",
            "allowed": ["excellent", "good", "fair", "poor"],
        },
        {"name": "smoker", "prompt": "Is the insured a smoker? Reply yes or no.", "type": "bool"},
        {
            "name": "coverage_amount",
            "prompt": "What coverage amount do you want in USD? (e.g. 500000)",
            "type": "float",
            "min_value": 1,
        },
        {"name": "term_years", "prompt": "Which term length do you want: 10, 20, or 30 years?", "type": "int", "allowed": [10, 20, 30]},
        {
            "name": "coverage_level",
            "prompt": "Which coverage level do you want: basic, standard, or comprehensive?",
            "type": "str",
            "allowed": ["basic", "standard", "comprehensive"],
        },
    ],
}


def collect_details(state: dict[str, Any], message: str | None = None) -> dict[str, Any]:
    service_type = state.get("service_type")
    if service_type not in FIELD_SPECS:
        _append_assistant_message(
            state,
            "I still need to know the service type before collecting booking details.",
        )
        state["intake_step"] = "identify"
        return state

    fields = FIELD_SPECS[service_type]
    collected = dict(state.get("collected_data", {}))
    current_field = state.get("current_field") or _next_missing_field(fields, collected)

    if current_field and message and message.strip():
        try:
            if service_type == "auto":
                collected = _merge_auto_multi_field_input(collected, current_field, message)
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


def _merge_auto_multi_field_input(
    collected: dict[str, Any],
    current_field: str,
    raw: str,
) -> dict[str, Any]:
    next_collected = dict(collected)
    lowered = raw.lower()
    compact = re.sub(r"\s+", " ", raw).strip()
    fields = FIELD_SPECS["auto"]

    parsed_sequential = _merge_auto_sequential_input(fields, next_collected, current_field, raw)
    if parsed_sequential is not None:
        next_collected = parsed_sequential

    if current_field == "vehicle_year":
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", compact)
        coverage_match = re.search(r"\b(basic|standard|comprehensive)\b", lowered)
        if coverage_match:
            next_collected.setdefault("coverage_level", coverage_match.group(1))

        remainder = compact
        if year_match:
            remainder = re.sub(r"\b(19\d{2}|20\d{2})\b", "", remainder, count=1).strip()
        remainder = re.sub(r"\bmodel\b", "", remainder, flags=re.IGNORECASE).strip()
        if coverage_match:
            remainder = re.sub(
                r"\b(basic|standard|comprehensive)\b",
                "",
                remainder,
                count=1,
                flags=re.IGNORECASE,
            ).strip()

        parts = [part for part in remainder.split() if part]
        if parts:
            next_collected.setdefault("vehicle_make", parts[0].title())
        if len(parts) >= 2:
            next_collected.setdefault("vehicle_model", " ".join(parts[1:]).title())

    elif current_field == "vehicle_make":
        cleaned = re.sub(r"\b(19\d{2}|20\d{2})\b", "", compact).strip()
        cleaned = re.sub(r"\bmodel\b", "", cleaned, flags=re.IGNORECASE).strip()
        parts = [part for part in cleaned.split() if part]
        if parts:
            next_collected.setdefault("vehicle_make", parts[0].title())
        if len(parts) >= 2:
            next_collected.setdefault("vehicle_model", " ".join(parts[1:]).title())

    elif current_field == "vehicle_model":
        cleaned = re.sub(r"\b(19\d{2}|20\d{2})\b", "", compact).strip()
        cleaned = re.sub(r"\bmodel\b", "", cleaned, flags=re.IGNORECASE).strip()
        if next_collected.get("vehicle_make"):
            make_prefix = str(next_collected["vehicle_make"])
            if cleaned.lower().startswith(make_prefix.lower()):
                cleaned = cleaned[len(make_prefix):].strip()
        if cleaned:
            next_collected.setdefault("vehicle_model", cleaned.title())

    elif current_field == "coverage_level":
        coverage_match = re.search(r"\b(basic|standard|comprehensive)\b", lowered)
        if coverage_match:
            next_collected.setdefault("coverage_level", coverage_match.group(1))

    return next_collected


def _merge_auto_sequential_input(
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
    if any(term in lowered for term in ("quote", "coverage", "policy", "insurance")):
        raise ValueError("Please enter the requested detail, not a new policy question.")

    if len(alpha_tokens) > 6:
        raise ValueError("Please keep the answer short and limited to the requested detail.")

    if min_length is not None and len(normalized) < min_length:
        raise ValueError("Please enter a valid text value.")

    if field_name == "location":
        if len(normalized) < 3:
            raise ValueError("Please enter a valid city or location.")
        if len(alpha_tokens) < 1:
            raise ValueError("Please enter a valid city or location.")
        if len(alpha_tokens) > 3:
            raise ValueError("Please enter only the city or location name.")
        if normalized.lower().startswith(("i ", "my ", "we ", "they ")):
            raise ValueError("Please enter only the city or location name.")
        lower_tokens = {token.lower() for token in alpha_tokens}
        if {"like", "love"} & lower_tokens:
            raise ValueError("Please enter a real city or location.")
        if len(alpha_tokens) == 1 and next(iter(lower_tokens)) in LOCATION_DENYLIST:
            raise ValueError("Please enter a real city or location, for example Makati, Manila, or Quezon City.")
        if not re.fullmatch(r"[A-Za-z\s,.-]+", normalized):
            raise ValueError("Please enter a valid city or location.")

    return normalized


def _range_error_message(
    field_name: str,
    *,
    min_value: float | int | None,
    max_value: float | int | None,
) -> str:
    if field_name == "year_built" and min_value is not None and max_value is not None:
        return f"Year built must be between {int(min_value)} and {int(max_value)}."
    if field_name == "vehicle_year" and min_value is not None and max_value is not None:
        return f"Vehicle year must be between {int(min_value)} and {int(max_value)}."
    if field_name == "estimated_value" and min_value is not None:
        return (
            "Please enter a more realistic property value in USD, "
            "for example 100000 or 350000."
        )
    if field_name == "accidents_last_5yr" and min_value is not None and max_value is not None:
        return (
            "Please enter a realistic accident count between "
            f"{int(min_value)} and {int(max_value)} for the last 5 years."
        )
    if field_name == "coverage_amount" and min_value is not None:
        return "Please enter a positive coverage amount."
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

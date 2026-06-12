from __future__ import annotations

from datetime import UTC, datetime

from nodes.collect_details import INTAKE_FIELDS, _coerce_value
from services.catalog import SERVICES


def validate_intake(state: dict, message: str | None = None) -> dict:
    collected = dict(state.get("collected_data", {}))
    service = state.get("service_type", "")

    # Defense-in-depth: re-validate each stored field.
    for spec in INTAKE_FIELDS:
        field_name = spec["name"]
        raw = collected.get(field_name)

        if raw is None:
            _append_assistant_message(
                state,
                f"I'm missing your {field_name.replace('_', ' ')}. "
                f"{spec['prompt']}",
            )
            state["intake_step"] = "collect"
            state["current_field"] = field_name
            return state

        # The "slot" field is stored as a UTC-naive ISO datetime string — validate
        # it directly with fromisoformat rather than re-running parse_slot_phrase
        # (which only accepts natural-language phrases, not ISO strings).
        if spec.get("type") == "slot":
            try:
                parsed = datetime.fromisoformat(str(raw))
                # Ensure it is still strictly in the future (compare as naive UTC).
                if parsed <= datetime.now(UTC).replace(tzinfo=None):
                    raise ValueError("Slot is in the past.")
            except ValueError as exc:
                collected.pop(field_name, None)
                state["collected_data"] = collected
                state["intake_step"] = "collect"
                state["current_field"] = field_name
                _append_assistant_message(
                    state,
                    f"That appointment time has already passed — what's the next day and time that works? "
                    f"{spec['prompt']}",
                )
                return state
            # Slot is valid — continue to next field.
            continue

        try:
            _coerce_value(
                field_name,
                spec.get("type", "str"),
                str(raw),
                allowed=spec.get("allowed"),
                min_value=spec.get("min_value"),
                max_value=spec.get("max_value"),
                min_length=spec.get("min_length"),
            )
        except ValueError as exc:
            collected.pop(field_name, None)
            state["collected_data"] = collected
            state["intake_step"] = "collect"
            state["current_field"] = field_name
            _append_assistant_message(state, f"{exc} {spec['prompt']}")
            return state

    # All fields valid — build the confirmation summary.
    service_label = SERVICES.get(service, {}).get("label", service)
    patient_name = collected["patient_name"]
    phone = collected["phone"]
    email = collected["email"]
    slot_iso = collected["preferred_slot"]

    dt = datetime.fromisoformat(slot_iso)
    # Portable day/hour formatting: avoid %-d and %-I (Linux-only).
    weekday = dt.strftime("%A")
    month = dt.strftime("%b")
    day = str(dt.day)          # no leading zero
    hour_12 = dt.hour % 12 or 12
    minute = dt.strftime("%M")
    ampm = "AM" if dt.hour < 12 else "PM"
    time_str = f"{weekday} {month} {day} at {hour_12}:{minute} {ampm}"

    summary = (
        f"Here's what I have: **{service_label}** for **{patient_name}**, "
        f"{time_str}, phone {phone}, confirmation to {email}. "
        "Reply **accept** to book it, **adjust** to change something, or **restart**."
    )
    _append_assistant_message(state, summary)
    state["intake_step"] = "confirm"
    return state


def _append_assistant_message(state: dict, content: str) -> None:
    messages = list(state.get("messages", []))
    messages.append({"role": "assistant", "content": content})
    state["messages"] = messages

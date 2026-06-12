"""Unit tests for dental intake slot parsing and field validators.

Tests the new phone / email / slot coercers and the parse_slot_phrase helper
that powers the 'slot' field type in collect_details.
"""
from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from nodes.collect_details import collect_details, parse_slot_phrase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_state(field: str, **collected) -> dict:
    return {
        "mode": "transactional",
        "intake_step": "collect",
        "service_type": "cleaning",
        "current_field": field,
        "collected_data": dict(collected),
        "messages": [{"role": "user", "content": "x"}],
    }


# ---------------------------------------------------------------------------
# Phone coercer
# ---------------------------------------------------------------------------

def test_phone_accepts_digits_with_punctuation():
    state = make_state("phone", patient_name="Maria Santos")
    out = collect_details(state, "(917) 555-0144")
    assert out["collected_data"]["phone"] == "9175550144"


def test_phone_rejects_short():
    state = make_state("phone", patient_name="Maria Santos")
    out = collect_details(state, "12345")
    assert "phone" not in out["collected_data"]  # invalid input never advances
    assert out["current_field"] == "phone"


def test_phone_rejects_alpha():
    state = make_state("phone", patient_name="Maria Santos")
    out = collect_details(state, "abc")
    assert "phone" not in out["collected_data"]
    assert out["current_field"] == "phone"


def test_phone_accepts_ten_digits():
    state = make_state("phone", patient_name="Maria Santos")
    out = collect_details(state, "9175550144")
    assert out["collected_data"]["phone"] == "9175550144"


def test_phone_accepts_plus_country_code():
    state = make_state("phone", patient_name="Maria Santos")
    out = collect_details(state, "+1 (917) 555-0144")
    assert out["collected_data"]["phone"] == "19175550144"


# ---------------------------------------------------------------------------
# Email coercer
# ---------------------------------------------------------------------------

def test_email_validated():
    state = make_state("email", patient_name="M S", phone="9175550144")
    out = collect_details(state, "maria at example dot com")
    assert out["current_field"] == "email"


def test_email_accepts_valid():
    state = make_state("email", patient_name="M S", phone="9175550144")
    out = collect_details(state, "maria@example.com")
    assert out["collected_data"]["email"] == "maria@example.com"


def test_email_lowercased():
    state = make_state("email", patient_name="M S", phone="9175550144")
    out = collect_details(state, "MARIA@EXAMPLE.COM")
    assert out["collected_data"]["email"] == "maria@example.com"


def test_email_rejects_no_at_sign():
    state = make_state("email", patient_name="M S", phone="9175550144")
    out = collect_details(state, "notanemail")
    assert "email" not in out["collected_data"]
    assert out["current_field"] == "email"


# ---------------------------------------------------------------------------
# Slot coercer — via collect_details
# ---------------------------------------------------------------------------

def test_slot_parses_weekday_time():
    state = make_state(
        "preferred_slot",
        patient_name="M S",
        phone="9175550144",
        email="m@example.com",
        patient_status="new",
    )
    out = collect_details(state, "Wednesday 2:30 pm")
    assert out["collected_data"]["preferred_slot"].endswith(":30:00")
    assert out["intake_step"] == "validate"  # last slot filled → advance


def test_slot_rejects_vague():
    state = make_state(
        "preferred_slot",
        patient_name="M S",
        phone="9175550144",
        email="m@example.com",
        patient_status="new",
    )
    out = collect_details(state, "whenever")
    assert "preferred_slot" not in out["collected_data"]
    assert out["current_field"] == "preferred_slot"


def test_slot_rejects_garbage():
    state = make_state(
        "preferred_slot",
        patient_name="M S",
        phone="9175550144",
        email="m@example.com",
        patient_status="new",
    )
    out = collect_details(state, "sometime soon")
    assert "preferred_slot" not in out["collected_data"]
    assert out["current_field"] == "preferred_slot"


# ---------------------------------------------------------------------------
# parse_slot_phrase — direct unit tests
# ---------------------------------------------------------------------------

def test_parse_slot_phrase_wednesday_2_30_pm():
    result = parse_slot_phrase("Wednesday 2:30 pm")
    assert result is not None
    assert result.minute == 30
    assert result.hour == 14
    assert result.weekday() == 2  # Wednesday = 2


def test_parse_slot_phrase_wed_2pm():
    result = parse_slot_phrase("wed 2pm")
    assert result is not None
    assert result.hour == 14
    assert result.minute == 0
    assert result.weekday() == 2


def test_parse_slot_phrase_returns_none_on_garbage():
    assert parse_slot_phrase("whenever") is None


def test_parse_slot_phrase_returns_none_on_vague():
    assert parse_slot_phrase("sometime soon") is None


def test_parse_slot_phrase_strictly_future():
    """Result must be strictly in the future (UTC)."""
    result = parse_slot_phrase("Monday 9am")
    assert result is not None
    now_utc = datetime.now(UTC)
    # parse_slot_phrase returns UTC-aware datetime internally; we compare
    # by making result aware if it isn't (v1: naive = UTC-naive, so attach UTC)
    aware = result.replace(tzinfo=UTC) if result.tzinfo is None else result
    assert aware > now_utc


def test_parse_slot_phrase_same_weekday_past_time_returns_next_week():
    """If today is the requested weekday but the time has passed, return next week."""
    now_utc = datetime.now(UTC)
    # Find today's weekday name
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today_name = weekday_names[now_utc.weekday()]

    # Request a time that is definitely in the past today (midnight = 12:00 AM)
    result = parse_slot_phrase(f"{today_name} 12:00 am")
    assert result is not None
    aware = result.replace(tzinfo=UTC) if result.tzinfo is None else result
    assert aware > now_utc
    # Should be 7 days out (next occurrence), not today
    assert (aware - now_utc).days >= 6


# ---------------------------------------------------------------------------
# Non-answer guard for str fields (dental denylist)
# ---------------------------------------------------------------------------

def test_dental_non_answer_guard_rejects_appointment_as_name():
    """'appointment' in a str field value is treated as a non-answer."""
    state = make_state("patient_name")
    out = collect_details(state, "book an appointment")
    assert "patient_name" not in out["collected_data"]
    assert out["current_field"] == "patient_name"


# ---------------------------------------------------------------------------
# Fix 1 — out-of-range hour guard in parse_slot_phrase
# ---------------------------------------------------------------------------

def test_parse_slot_phrase_rejects_hour_99_pm():
    """'friday 99 pm' must return None (not raise ValueError)."""
    assert parse_slot_phrase("friday 99 pm") is None


def test_parse_slot_phrase_rejects_hour_13_pm():
    """'monday 13 pm' must return None (13 is not a valid 12-h clock hour)."""
    assert parse_slot_phrase("monday 13 pm") is None


def test_collect_details_out_of_range_hour_returns_clean_message():
    """End-to-end: an out-of-range hour must yield the friendly reprompt, not a Python error."""
    state = make_state(
        "preferred_slot",
        patient_name="M S",
        phone="9175550144",
        email="m@example.com",
        patient_status="new",
    )
    out = collect_details(state, "friday 99 pm")
    assert "preferred_slot" not in out["collected_data"]
    reply = out["messages"][-1]["content"]
    assert "couldn't read that time" in reply
    assert "0..23" not in reply


# ---------------------------------------------------------------------------
# Fix 2 — word-boundary non-answer guard (near-miss names must pass)
# ---------------------------------------------------------------------------

def test_name_with_near_miss_word_is_accepted():
    """'Maria Bookington' should NOT be rejected — 'booking' appears as a substring
    but not as a whole word."""
    state = make_state("patient_name")
    out = collect_details(state, "Maria Bookington")
    assert out["collected_data"].get("patient_name") == "Maria Bookington"


def test_literal_non_answer_is_rejected():
    """'I need an appointment' must still be caught by the guard."""
    state = make_state("patient_name")
    out = collect_details(state, "I need an appointment")
    assert "patient_name" not in out["collected_data"]
    assert out["current_field"] == "patient_name"


# ---------------------------------------------------------------------------
# Fix 3 — optional "at" separator in slot regex
# ---------------------------------------------------------------------------

def test_parse_slot_phrase_with_at_separator():
    """'wednesday at 2:30 pm' should parse identically to 'wednesday 2:30 pm'."""
    result = parse_slot_phrase("wednesday at 2:30 pm")
    assert result is not None
    assert result.hour == 14
    assert result.minute == 30
    assert result.weekday() == 2  # Wednesday

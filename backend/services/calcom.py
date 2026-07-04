"""Cal.com booking client for front-desk appointment requests.

Thin stdlib-only wrapper (mirrors the request style of ``services/llm.py``):
one POST to the Cal.com v2 bookings API.

Docs: https://cal.com/docs/api-reference/v2/bookings/create-a-booking

The start time is computed deterministically — the next business day
(Saturdays and Sundays skipped) at 09:00 / 13:00 / 17:00 UTC for a
morning / afternoon / evening ``preferred_time``; services that do not
collect a preferred time (emergency, cosmetic) default to morning.

Demo-friendly by design: when ``CALCOM_API_KEY`` / ``CALCOM_EVENT_TYPE_ID``
are missing the client never touches the network and reports ``dry_run``;
any request failure is caught, logged, and reported as an ``error`` result
so the accept turn always succeeds.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta

from env import load_project_env
from services.front_desk import IntegrationResult

load_project_env()

CALCOM_BOOKINGS_URL = "https://api.cal.com/v2/bookings"
CALCOM_API_VERSION = "2024-08-13"
DEFAULT_TIMEZONE = "UTC"
DEFAULT_FALLBACK_EMAIL = "front-desk@ivory-dental.example"
DEFAULT_TIMEOUT_SECONDS = 10.0
INTEGRATION_NAME = "Cal.com booking"

_SLOT_HOURS_UTC = {"morning": 9, "afternoon": 13, "evening": 17}

logger = logging.getLogger("ivory.calcom")


def next_business_day_start(
    preferred_time: str | None,
    *,
    now: datetime | None = None,
) -> datetime:
    """Next weekday (Mon–Fri) at the deterministic UTC slot for *preferred_time*."""
    hour = _SLOT_HOURS_UTC.get((preferred_time or "").strip().lower(), _SLOT_HOURS_UTC["morning"])
    current = now or datetime.now(UTC)
    day = current.date() + timedelta(days=1)
    while day.weekday() >= 5:  # Saturday=5 / Sunday=6 — roll forward to Monday
        day += timedelta(days=1)
    return datetime(day.year, day.month, day.day, hour, tzinfo=UTC)


def create_booking(
    *,
    service_type: str,
    attendee_name: str,
    attendee_email: str | None = None,
    attendee_phone: str | None = None,
    preferred_time: str | None = None,
) -> IntegrationResult:
    """Request a Cal.com booking; dry-run locally when unconfigured."""
    api_key = os.getenv("CALCOM_API_KEY", "").strip()
    event_type_id = os.getenv("CALCOM_EVENT_TYPE_ID", "").strip()
    timezone_name = os.getenv("CLINIC_TIMEZONE", "").strip() or DEFAULT_TIMEZONE

    start = next_business_day_start(preferred_time)
    start_iso = start.isoformat().replace("+00:00", "Z")
    slot_label = f"{start:%A, %B %d} at {start:%H:%M} UTC"

    if not api_key or not event_type_id:
        return IntegrationResult(
            name=INTEGRATION_NAME,
            status="dry_run",
            detail="Cal.com (demo mode): booking request recorded locally",
        )

    try:
        event_type_id_int = int(event_type_id)
    except ValueError:
        logger.error("CALCOM_EVENT_TYPE_ID is not an integer: %r", event_type_id)
        return IntegrationResult(
            name=INTEGRATION_NAME,
            status="error",
            detail="Cal.com booking could not be requested (CALCOM_EVENT_TYPE_ID must be an integer).",
        )

    # Cal.com v2 requires an attendee email. Phone-only intakes (emergency)
    # collect no email, so fall back to a configurable clinic inbox — without
    # it, every emergency booking would 400. Configure CALCOM_FALLBACK_EMAIL
    # to route these to a real address the front desk monitors.
    fallback_email = os.getenv("CALCOM_FALLBACK_EMAIL", "").strip() or DEFAULT_FALLBACK_EMAIL
    attendee: dict[str, str] = {
        "name": attendee_name,
        "email": attendee_email or fallback_email,
        "timeZone": timezone_name,
    }
    if attendee_phone:
        attendee["phoneNumber"] = attendee_phone

    payload = {
        "start": start_iso,
        "eventTypeId": event_type_id_int,
        "attendee": attendee,
        "metadata": {"service_type": service_type},
    }
    request = urllib.request.Request(
        CALCOM_BOOKINGS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "cal-api-version": CALCOM_API_VERSION,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            response.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        logger.error("Cal.com booking failed — %s", exc)
        return IntegrationResult(
            name=INTEGRATION_NAME,
            status="error",
            detail=f"Cal.com booking could not be requested ({_describe_error(exc)}).",
        )

    return IntegrationResult(
        name=INTEGRATION_NAME,
        status="booked",
        detail=f"Appointment requested for {slot_label}.",
    )


def _describe_error(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    return exc.__class__.__name__

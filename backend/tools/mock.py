"""In-memory mock implementations of the booking tool layer.

These are the same interface production uses — keyless demo is architectural,
not a test hack.  They are deterministic and offline, making them safe for
integration tests without any external credentials.

Each call to ``bundle()`` returns a *fresh* ToolBundle with independent
MockBooking / MockCrm / MockEmail instances, so ``_bookings``, ``_leads``,
and ``_sends`` are local to a single invocation.  Idempotency is handled by
graph state (``booking_result.booking_uid``), not by these recording lists.
The lists are still useful when a ToolBundle is injected directly into
``book_appointment`` in unit tests that inspect side-effects.

Availability rules (deterministic, no I/O):
  - Monday–Thursday, 09:00–16:59 UTC → available
  - Friday, Saturday, Sunday → unavailable
  - Outside 09:00–16:59 → unavailable
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from tools.base import ToolBundle, ToolResult


class MockBooking:
    """In-memory calendar stub.

    Weekdays Mon–Thu, hours 09–16 (start-hour, so a visit that begins at 16:xx
    still fits before 17:00) are available.  Everything else is blocked.
    """

    def __init__(self) -> None:
        self._bookings: list[dict] = []

    def check_availability(self, service: str, start: datetime) -> ToolResult:
        # datetime.weekday(): Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
        if start.weekday() >= 4:  # Friday (4), Saturday (5), Sunday (6)
            return ToolResult(ok=False, error="Slot unavailable — no weekend or Friday appointments.")
        if not (9 <= start.hour <= 16):
            return ToolResult(ok=False, error="Slot unavailable — outside office hours (9 AM–5 PM).")
        return ToolResult(ok=True, data={"available": True})

    def create_booking(
        self, service: str, start: datetime, name: str, email: str
    ) -> ToolResult:
        uid = f"mock_{uuid4().hex[:8]}"
        record = {
            "booking_uid": uid,
            "service": service,
            "start": start.isoformat(),
            "name": name,
            "email": email,
        }
        self._bookings.append(record)
        return ToolResult(ok=True, data={"booking_uid": uid})


class MockCrm:
    """In-memory CRM stub, keyed by session_id."""

    def __init__(self) -> None:
        self._leads: dict[str, dict] = {}

    def upsert_lead(self, lead: dict) -> ToolResult:
        session_id = lead.get("session_id", str(uuid4().hex[:8]))
        lead_record_id = f"rec_{uuid4().hex[:8]}"
        self._leads[session_id] = {**lead, "lead_record_id": lead_record_id}
        return ToolResult(ok=True, data={"lead_record_id": lead_record_id})


class MockEmail:
    """In-memory email stub — always succeeds, records sends."""

    def __init__(self) -> None:
        self._sends: list[dict] = []

    def send_confirmation(self, to: str, booking: dict) -> ToolResult:
        self._sends.append({"to": to, "booking": booking})
        return ToolResult(ok=True, data={"message_id": f"msg_{uuid4().hex[:8]}"})


def bundle() -> ToolBundle:
    """Return a fresh ToolBundle with independent mock instances."""
    return ToolBundle(
        booking=MockBooking(),
        crm=MockCrm(),
        email=MockEmail(),
    )

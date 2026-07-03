"""Front-desk integration orchestrator for accepted visit estimates.

Coordinates the three thin clients — Airtable CRM lead capture, Cal.com
appointment booking, and Resend email confirmation — for an explicitly
accepted visit estimate. The interface below (``IntegrationResult`` and the
``process_accept`` signature) is fixed by the spec (section 9.4) and must not
change. It is called from the confirm node's accept branch only; no
integration ever fires before an explicit ``accept``.

Failure policy: ``process_accept`` never raises. Each client already turns
missing configuration into a ``dry_run`` (no network call) and request
failures into ``error`` results; the orchestrator adds a final safety net so
any unexpected exception still becomes an ``error`` result for that
integration and the accept turn succeeds.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("ivory.front_desk")

_SERVICE_LABELS = {
    "cleaning": "cleaning visit",
    "emergency": "emergency visit",
    "cosmetic": "cosmetic consultation",
}


@dataclass(frozen=True)
class IntegrationResult:
    name: str      # "Airtable CRM" | "Cal.com booking" | "Email confirmation"
    status: str    # created | booked | sent | dry_run | skipped | error
    detail: str    # one human sentence, shown verbatim in chat


def process_accept(
    service_type: str,
    collected: dict[str, Any],
    estimate: dict[str, Any],
) -> list[IntegrationResult]:
    """Run the three front-desk integrations for an accepted visit estimate.

    Returns exactly three results, in the order rendered by the confirm
    node's "Front desk actions" block: Airtable CRM, Cal.com booking,
    Email confirmation. Never raises.
    """
    return [
        _run("Airtable CRM", lambda: _create_lead(service_type, collected, estimate)),
        _run("Cal.com booking", lambda: _create_booking(service_type, collected)),
        _run("Email confirmation", lambda: _send_confirmation(service_type, collected, estimate)),
    ]


def _run(name: str, call: Callable[[], IntegrationResult]) -> IntegrationResult:
    """Invoke one integration, converting any escaped exception into an error result."""
    try:
        return call()
    except Exception as exc:  # noqa: BLE001 — the accept turn must always succeed
        logger.error("Front-desk integration %s failed unexpectedly — %s", name, exc)
        return IntegrationResult(
            name=name,
            status="error",
            detail=f"{name} failed unexpectedly ({exc.__class__.__name__}).",
        )


def _create_lead(
    service_type: str,
    collected: dict[str, Any],
    estimate: dict[str, Any],
) -> IntegrationResult:
    # Imported lazily: the client modules import IntegrationResult from here
    # (same pattern as graph.py's inline validate_visit import).
    from services import airtable

    fields = {
        "Name": str(collected.get("patient_name") or ""),
        "Contact": str(collected.get("contact_email") or collected.get("contact_phone") or ""),
        "Service": service_type,
        "Details": json.dumps(collected, sort_keys=True, default=str),
        "Estimate Low": estimate.get("estimate_low"),
        "Estimate High": estimate.get("estimate_high"),
        "Status": "New",
    }
    return airtable.create_lead(fields)


def _create_booking(service_type: str, collected: dict[str, Any]) -> IntegrationResult:
    from services import calcom

    return calcom.create_booking(
        service_type=service_type,
        attendee_name=str(collected.get("patient_name") or "Ivory patient"),
        attendee_email=str(collected.get("contact_email") or "").strip() or None,
        attendee_phone=str(collected.get("contact_phone") or "").strip() or None,
        preferred_time=str(collected.get("preferred_time") or "").strip() or None,
    )


def _send_confirmation(
    service_type: str,
    collected: dict[str, Any],
    estimate: dict[str, Any],
) -> IntegrationResult:
    from services import resend_email

    return resend_email.send_confirmation(
        to_email=str(collected.get("contact_email") or "").strip() or None,
        subject="Your Ivory Dental Studio visit request",
        text=_confirmation_text(service_type, collected, estimate),
    )


def _confirmation_text(
    service_type: str,
    collected: dict[str, Any],
    estimate: dict[str, Any],
) -> str:
    """Plain-text confirmation body; deterministic, no LLM involved."""
    patient_name = str(collected.get("patient_name") or "there")
    service_label = _SERVICE_LABELS.get(service_type, "dental visit")
    lines = [
        f"Hi {patient_name},",
        "",
        f"Thanks for choosing Ivory Dental Studio — we received your {service_label} request.",
    ]
    estimate_low = estimate.get("estimate_low")
    estimate_high = estimate.get("estimate_high")
    if estimate_low is not None and estimate_high is not None:
        currency = str(estimate.get("currency") or "USD")
        lines += ["", f"Estimated cost: ${estimate_low}–${estimate_high} {currency}."]
    disclaimer = str(estimate.get("disclaimer") or "").strip()
    if disclaimer:
        lines.append(disclaimer)
    lines += [
        "",
        "Our front desk will reach out shortly to confirm your appointment time.",
        "",
        "— Ivory, the AI front desk at Ivory Dental Studio",
    ]
    return "\n".join(lines)

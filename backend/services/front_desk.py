"""Front-desk integration orchestrator for accepted visit estimates.

PLACEHOLDER: the integrations agent replaces the ``process_accept`` body with
the real Airtable / Cal.com / Resend clients. The interface below —
``IntegrationResult`` and the ``process_accept`` signature — is fixed by the
spec (section 9.4) and must not change. It is called from the confirm node's
accept branch only; no integration ever fires before an explicit ``accept``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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

    Placeholder behavior: every integration reports ``dry_run`` so the accept
    turn is fully functional before the real clients land.
    """
    return [
        IntegrationResult(
            name="Airtable CRM",
            status="dry_run",
            detail="Airtable (demo mode): lead captured locally",
        ),
        IntegrationResult(
            name="Cal.com booking",
            status="dry_run",
            detail="Cal.com (demo mode): booking request recorded locally",
        ),
        IntegrationResult(
            name="Email confirmation",
            status="dry_run",
            detail="Resend (demo mode): confirmation email drafted locally",
        ),
    ]

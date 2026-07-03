"""Resend email client for front-desk visit confirmations.

Thin stdlib-only wrapper (mirrors the request style of ``services/llm.py``):
one POST to the Resend transactional email API.

Docs: https://resend.com/docs/api-reference/emails/send-email

The emergency flow collects a phone number instead of an email, so a missing
recipient address is a deliberate ``skipped`` result — never an error.

Demo-friendly by design: when ``RESEND_API_KEY`` is missing the client never
touches the network and reports ``dry_run``; any request failure is caught,
logged, and reported as an ``error`` result so the accept turn always
succeeds.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

from env import load_project_env
from services.front_desk import IntegrationResult

load_project_env()

RESEND_EMAILS_URL = "https://api.resend.com/emails"
DEFAULT_FROM = "Ivory <onboarding@resend.dev>"
DEFAULT_TIMEOUT_SECONDS = 10.0
INTEGRATION_NAME = "Email confirmation"

logger = logging.getLogger("ivory.resend")


def send_confirmation(
    *,
    to_email: str | None,
    subject: str,
    text: str,
) -> IntegrationResult:
    """Send a confirmation email; skip when there is no address on file."""
    recipient = (to_email or "").strip()
    if not recipient:
        return IntegrationResult(
            name=INTEGRATION_NAME,
            status="skipped",
            detail="No email on file for this visit (phone contact only) — the front desk will call instead.",
        )

    api_key = os.getenv("RESEND_API_KEY", "").strip()
    from_address = os.getenv("RESEND_FROM", "").strip() or DEFAULT_FROM

    if not api_key:
        return IntegrationResult(
            name=INTEGRATION_NAME,
            status="dry_run",
            detail="Resend (demo mode): confirmation email drafted locally",
        )

    payload = {
        "from": from_address,
        "to": [recipient],
        "subject": subject,
        "text": text,
    }
    request = urllib.request.Request(
        RESEND_EMAILS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            response.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        logger.error("Resend confirmation email failed — %s", exc)
        return IntegrationResult(
            name=INTEGRATION_NAME,
            status="error",
            detail=f"Confirmation email could not be sent ({_describe_error(exc)}).",
        )

    return IntegrationResult(
        name=INTEGRATION_NAME,
        status="sent",
        detail=f"Confirmation email sent to {recipient}.",
    )


def _describe_error(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    return exc.__class__.__name__

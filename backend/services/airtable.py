"""Airtable CRM client for front-desk lead capture.

Thin stdlib-only wrapper (mirrors the request style of ``services/llm.py``):
one POST to the Airtable REST API creating a single lead record.

Docs: https://airtable.com/developers/web/api/create-records

Demo-friendly by design: when ``AIRTABLE_API_KEY`` / ``AIRTABLE_BASE_ID`` are
missing the client never touches the network and reports ``dry_run``; any
request failure is caught, logged, and reported as an ``error`` result so the
accept turn always succeeds.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from env import load_project_env
from services.front_desk import IntegrationResult

load_project_env()

AIRTABLE_API_URL = "https://api.airtable.com/v0"
DEFAULT_TABLE_NAME = "Leads"
DEFAULT_TIMEOUT_SECONDS = 10.0
INTEGRATION_NAME = "Airtable CRM"

logger = logging.getLogger("ivory.airtable")


def create_lead(fields: dict[str, Any]) -> IntegrationResult:
    """Create one lead record in Airtable; dry-run locally when unconfigured."""
    api_key = os.getenv("AIRTABLE_API_KEY", "").strip()
    base_id = os.getenv("AIRTABLE_BASE_ID", "").strip()
    table_name = os.getenv("AIRTABLE_TABLE_NAME", "").strip() or DEFAULT_TABLE_NAME

    if not api_key or not base_id:
        return IntegrationResult(
            name=INTEGRATION_NAME,
            status="dry_run",
            detail="Airtable (demo mode): lead captured locally",
        )

    url = f"{AIRTABLE_API_URL}/{base_id}/{urllib.parse.quote(table_name)}"
    payload = {"records": [{"fields": fields}]}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
        parsed = json.loads(body) if body.strip() else {}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        logger.error("Airtable lead creation failed — %s", exc)
        return IntegrationResult(
            name=INTEGRATION_NAME,
            status="error",
            detail=f"Airtable lead could not be saved ({_describe_error(exc)}).",
        )

    record_id = _first_record_id(parsed)
    suffix = f" (record {record_id})" if record_id else ""
    return IntegrationResult(
        name=INTEGRATION_NAME,
        status="created",
        detail=f"New lead saved to the clinic CRM{suffix}.",
    )


def _first_record_id(parsed: Any) -> str:
    """Extract the created record id from Airtable's response, if present."""
    if not isinstance(parsed, dict):
        return ""
    records = parsed.get("records")
    if isinstance(records, list) and records and isinstance(records[0], dict):
        return str(records[0].get("id", "") or "")
    return ""


def _describe_error(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    return exc.__class__.__name__

"""Tool registry — single entry point for selecting the active ToolBundle.

Set TOOLS_MODE=mock (default) for the in-memory demo bundle.
Set TOOLS_MODE=live to load live Cal.com / Airtable / Resend adapters (Phase 4).
"""
from __future__ import annotations

import os

from tools import base, mock


def get_tools() -> base.ToolBundle:
    mode = os.environ.get("TOOLS_MODE", "mock")
    if mode == "mock":
        return mock.bundle()
    from tools import live  # Phase 4 — live Cal.com/Airtable/Resend adapters
    return live.bundle()

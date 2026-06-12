"""Protocol definitions for the booking tool layer.

All production and mock implementations satisfy these protocols.  This module
has zero runtime dependencies — import it freely from any node.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import NamedTuple, Protocol


@dataclass
class ToolResult:
    ok: bool
    data: dict = field(default_factory=dict)
    error: str | None = None


class BookingTool(Protocol):
    def check_availability(self, service: str, start: datetime) -> ToolResult: ...
    def create_booking(
        self, service: str, start: datetime, name: str, email: str
    ) -> ToolResult: ...


class CrmTool(Protocol):
    def upsert_lead(self, lead: dict) -> ToolResult: ...


class EmailTool(Protocol):
    def send_confirmation(self, to: str, booking: dict) -> ToolResult: ...


class ToolBundle(NamedTuple):
    booking: BookingTool
    crm: CrmTool
    email: EmailTool

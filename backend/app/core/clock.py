"""Time in one place so tests can control it. Business dates use South African time (SAST, UTC+2)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

SAST = ZoneInfo("Africa/Johannesburg")


def now() -> datetime:
    return datetime.now(timezone.utc)


def today() -> date:
    return now().astimezone(SAST).date()

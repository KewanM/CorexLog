from __future__ import annotations

from datetime import datetime

from cortexlog.db.models import AI_DATETIME_FORMAT


def parse_ai_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, AI_DATETIME_FORMAT)


def format_human_datetime(value: datetime | None) -> str:
    if value is None:
        return "No due date"
    return value.strftime("%Y-%m-%d %I:%M %p")

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


DATETIME_STORAGE_FORMAT = "%Y-%m-%d %H:%M:%S"
AI_DATETIME_FORMAT = "%Y-%m-%d %H:%M"


@dataclass
class NoteRecord:
    id: int
    content: str
    created_at: datetime


@dataclass
class TaskRecord:
    id: int
    content: str
    status: str
    created_at: datetime
    due_date: datetime | None


@dataclass
class EventRecord:
    id: int
    title: str
    event_time: datetime
    created_at: datetime


@dataclass
class TodayItems:
    tasks: list[TaskRecord]
    events: list[EventRecord]


def parse_stored_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.strptime(value, DATETIME_STORAGE_FORMAT)


def serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime(DATETIME_STORAGE_FORMAT)


def note_from_row(row: Any) -> NoteRecord:
    return NoteRecord(
        id=row["id"],
        content=row["content"],
        created_at=parse_stored_datetime(row["created_at"]) or datetime.now(),
    )


def task_from_row(row: Any) -> TaskRecord:
    return TaskRecord(
        id=row["id"],
        content=row["content"],
        status=row["status"],
        created_at=parse_stored_datetime(row["created_at"]) or datetime.now(),
        due_date=parse_stored_datetime(row["due_date"]),
    )


def event_from_row(row: Any) -> EventRecord:
    return EventRecord(
        id=row["id"],
        title=row["title"],
        event_time=parse_stored_datetime(row["event_time"]) or datetime.now(),
        created_at=parse_stored_datetime(row["created_at"]) or datetime.now(),
    )

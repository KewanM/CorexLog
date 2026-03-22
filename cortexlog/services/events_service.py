from __future__ import annotations

from datetime import datetime

from cortexlog.db.database import database_manager
from cortexlog.db.models import EventRecord, TodayItems, event_from_row, serialize_datetime
from cortexlog.services.tasks_service import tasks_service


class EventsService:
    def create_event(self, title: str, event_time: datetime) -> int:
        created_at = serialize_datetime(datetime.now())
        with database_manager.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (title, event_time, created_at)
                VALUES (?, ?, ?)
                """,
                (title.strip(), serialize_datetime(event_time), created_at),
            )
            return int(cursor.lastrowid)

    def get_events_for_day(self, day: datetime) -> list[EventRecord]:
        day_start = day.strftime("%Y-%m-%d 00:00:00")
        day_end = day.strftime("%Y-%m-%d 23:59:59")
        with database_manager.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, title, event_time, created_at
                FROM events
                WHERE datetime(event_time) BETWEEN datetime(?) AND datetime(?)
                ORDER BY datetime(event_time)
                """,
                (day_start, day_end),
            ).fetchall()
        return [event_from_row(row) for row in rows]

    def get_today(self) -> TodayItems:
        today = datetime.now()
        return TodayItems(
            tasks=tasks_service.get_tasks_for_day(today),
            events=self.get_events_for_day(today),
        )


events_service = EventsService()

from __future__ import annotations

from datetime import datetime

from cortexlog.db.database import database_manager
from cortexlog.db.models import TaskRecord, task_from_row, serialize_datetime


class TasksService:
    def create_task(self, content: str, due_date: datetime | None = None) -> int:
        created_at = serialize_datetime(datetime.now())
        with database_manager.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (content, status, created_at, due_date)
                VALUES (?, 'open', ?, ?)
                """,
                (content.strip(), created_at, serialize_datetime(due_date)),
            )
            return int(cursor.lastrowid)

    def get_tasks(self, status: str = "open") -> list[TaskRecord]:
        with database_manager.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, content, status, created_at, due_date
                FROM tasks
                WHERE status = ?
                ORDER BY due_date IS NULL, datetime(due_date), datetime(created_at) DESC
                """,
                (status,),
            ).fetchall()
        return [task_from_row(row) for row in rows]

    def get_tasks_for_day(self, day: datetime) -> list[TaskRecord]:
        day_start = day.strftime("%Y-%m-%d 00:00:00")
        day_end = day.strftime("%Y-%m-%d 23:59:59")
        with database_manager.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, content, status, created_at, due_date
                FROM tasks
                WHERE status = 'open'
                  AND due_date IS NOT NULL
                  AND datetime(due_date) BETWEEN datetime(?) AND datetime(?)
                ORDER BY datetime(due_date)
                """,
                (day_start, day_end),
            ).fetchall()
        return [task_from_row(row) for row in rows]


tasks_service = TasksService()

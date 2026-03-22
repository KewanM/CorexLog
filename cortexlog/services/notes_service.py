from __future__ import annotations

from datetime import datetime

from cortexlog.db.database import database_manager
from cortexlog.db.models import NoteRecord, note_from_row, serialize_datetime


class NotesService:
    def create_note(self, content: str) -> int:
        created_at = serialize_datetime(datetime.now())
        with database_manager.connection() as conn:
            cursor = conn.execute(
                "INSERT INTO notes (content, created_at) VALUES (?, ?)",
                (content.strip(), created_at),
            )
            return int(cursor.lastrowid)

    def get_notes(self, limit: int = 10) -> list[NoteRecord]:
        with database_manager.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, content, created_at
                FROM notes
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [note_from_row(row) for row in rows]


notes_service = NotesService()

from __future__ import annotations

import csv
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


LOGGER = logging.getLogger(__name__)
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "database" / "cortexlog.db"


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        content TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('open', 'done')),
        created_at TEXT NOT NULL,
        due_date TEXT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        event_time TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS raw_logs (
        id INTEGER PRIMARY KEY,
        raw_text TEXT NOT NULL,
        ai_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY,
        timestamp TEXT NOT NULL,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        original_text TEXT NOT NULL,
        enhanced_text TEXT NOT NULL,
        final_version_saved TEXT NOT NULL
            CHECK(final_version_saved IN ('original', 'enhanced', 'both')),
        tags TEXT,
        status TEXT NOT NULL CHECK(status IN ('draft', 'saved', 'cancelled'))
    )
    """,
)


class DatabaseManager:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            for statement in SCHEMA_STATEMENTS:
                conn.execute(statement)
        LOGGER.info("Database initialized at %s", self.db_path)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def export_table_to_csv(self, table_name: str, output_path: str | Path) -> Path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        with self.connection() as conn:
            rows = conn.execute(f"SELECT * FROM {table_name} ORDER BY id").fetchall()

        fieldnames = list(rows[0].keys()) if rows else self._get_table_columns(table_name)
        with destination.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))

        return destination

    def _get_table_columns(self, table_name: str) -> list[str]:
        with self.connection() as conn:
            rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return [str(row["name"]) for row in rows]


database_manager = DatabaseManager()

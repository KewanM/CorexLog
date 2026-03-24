from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from cortexlog.db.database import database_manager
from cortexlog.db.models import serialize_datetime


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOGS_ROOT = DEFAULT_ROOT / "logs"

CATEGORY_DIRECTORIES = {
    "diary": "diary",
    "book": "book",
    "task": "tasks",
    "idea": "ideas",
    "event": "events",
    "goal": "goals",
    "note": "notes",
}


@dataclass(frozen=True)
class SavedEntry:
    entry_id: int
    category: str
    file_path: Path
    save_type: str


class StorageManager:
    def __init__(self, logs_root: Path | None = None) -> None:
        self.logs_root = logs_root or DEFAULT_LOGS_ROOT

    def initialize(self) -> None:
        for directory_name in CATEGORY_DIRECTORIES.values():
            (self.logs_root / directory_name).mkdir(parents=True, exist_ok=True)
        (self.logs_root / "system").mkdir(parents=True, exist_ok=True)

    def save_entry(
        self,
        *,
        category: str,
        title: str,
        original_text: str,
        enhanced_text: str,
        final_version_saved: str,
        tags: list[str],
    ) -> SavedEntry:
        self.initialize()
        timestamp = datetime.now().replace(microsecond=0)
        file_path = self._build_file_path(category=category, title=title, timestamp=timestamp)
        content = self._build_file_content(
            title=title,
            category=category,
            original_text=original_text,
            enhanced_text=enhanced_text,
            final_version_saved=final_version_saved,
            tags=tags,
            timestamp=timestamp,
        )
        file_path.write_text(content, encoding="utf-8")

        with database_manager.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO entries (
                    timestamp,
                    category,
                    title,
                    original_text,
                    enhanced_text,
                    final_version_saved,
                    tags,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'saved')
                """,
                (
                    serialize_datetime(timestamp),
                    category,
                    title,
                    original_text,
                    enhanced_text,
                    final_version_saved,
                    ",".join(tags),
                ),
            )
        return SavedEntry(
            entry_id=int(cursor.lastrowid),
            category=category,
            file_path=file_path,
            save_type=final_version_saved,
        )

    def _build_file_path(self, *, category: str, title: str, timestamp: datetime) -> Path:
        folder_name = CATEGORY_DIRECTORIES[category]
        slug = self._slugify(title or f"{category}-entry")
        filename = f"{timestamp.strftime('%Y-%m-%d')}_{slug}.txt"
        return self.logs_root / folder_name / filename

    def _build_file_content(
        self,
        *,
        title: str,
        category: str,
        original_text: str,
        enhanced_text: str,
        final_version_saved: str,
        tags: list[str],
        timestamp: datetime,
    ) -> str:
        lines = [
            f"# {title or 'Untitled Entry'}",
            "",
            f"- Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- Category: {category}",
            f"- Saved version: {final_version_saved}",
            f"- Tags: {', '.join(tags) if tags else 'none'}",
            "",
        ]
        if final_version_saved in {"original", "both"}:
            lines.extend(["## Original Text", "", original_text, ""])
        if final_version_saved in {"enhanced", "both"}:
            lines.extend(["## Enhanced Text", "", enhanced_text, ""])
        return "\n".join(lines).strip() + "\n"

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return slug or "entry"


storage_manager = StorageManager()

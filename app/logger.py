from __future__ import annotations

from datetime import datetime
from pathlib import Path


DEFAULT_LOG_FILE = Path(__file__).resolve().parents[1] / "logs" / "system" / "system_log.txt"


class SystemActionLogger:
    def __init__(self, log_file: Path | None = None) -> None:
        self.log_file = log_file or DEFAULT_LOG_FILE

    def log_action(
        self,
        action: str,
        category: str,
        title: str,
        save_type: str,
    ) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = (
            f"{timestamp} | action={action} | category={category} "
            f"| title={title or 'untitled'} | save_type={save_type}\n"
        )
        with self.log_file.open("a", encoding="utf-8") as handle:
            handle.write(line)


system_action_logger = SystemActionLogger()

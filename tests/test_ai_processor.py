from __future__ import annotations

from datetime import datetime

import pytest

from cortexlog.ai.processor import AIProcessor, AIValidationError


def test_local_fallback_parses_task_with_due_date() -> None:
    processor = AIProcessor()

    parsed = processor.local_fallback_parse("Finish the report tomorrow at 3pm")

    assert parsed.source == "local"
    assert len(parsed.tasks) == 1
    assert parsed.tasks[0]["content"] == "Finish the report"
    assert isinstance(parsed.tasks[0]["due_date"], str)
    due_date = datetime.strptime(parsed.tasks[0]["due_date"], "%Y-%m-%d %H:%M")
    assert due_date.hour == 15


def test_local_fallback_parses_event() -> None:
    processor = AIProcessor()

    parsed = processor.local_fallback_parse("Doctor appointment next monday at 9am")

    assert parsed.source == "local"
    assert len(parsed.events) == 1
    assert parsed.events[0]["title"] == "Doctor appointment"
    assert parsed.events[0]["event_time"].endswith("09:00")


def test_validate_json_rejects_unexpected_keys() -> None:
    processor = AIProcessor()

    with pytest.raises(AIValidationError):
        processor.validate_json('{"notes": [], "tasks": [], "events": [], "extra": []}')

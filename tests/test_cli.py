from __future__ import annotations

from datetime import datetime

from typer.testing import CliRunner

from cortexlog.cli.commands import app
from cortexlog.db.database import database_manager
from cortexlog.services.events_service import events_service
from cortexlog.services.notes_service import notes_service
from cortexlog.services.tasks_service import tasks_service


runner = CliRunner()


def test_tasks_command_shows_open_tasks(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database_manager, "db_path", tmp_path / "test.db")
    database_manager.initialize()
    tasks_service.create_task("Ship CI workflow")

    result = runner.invoke(app, ["tasks"])

    assert result.exit_code == 0
    assert "Open Tasks" in result.stdout
    assert "Ship CI workflow" in result.stdout


def test_notes_command_shows_recent_notes(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database_manager, "db_path", tmp_path / "test.db")
    database_manager.initialize()
    notes_service.create_note("Document branch policy")

    result = runner.invoke(app, ["notes"])

    assert result.exit_code == 0
    assert "Recent Notes" in result.stdout
    assert "Document branch policy" in result.stdout


def test_today_command_shows_tasks_and_events(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database_manager, "db_path", tmp_path / "test.db")
    database_manager.initialize()
    now = datetime.now().replace(second=0, microsecond=0)
    tasks_service.create_task("Review pull request", due_date=now)
    events_service.create_event("Sprint demo", event_time=now)

    result = runner.invoke(app, ["today"])

    assert result.exit_code == 0
    assert "Today's Tasks" in result.stdout
    assert "Review pull request" in result.stdout
    assert "Today's Events" in result.stdout
    assert "Sprint demo" in result.stdout

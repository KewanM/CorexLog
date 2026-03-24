from __future__ import annotations

import sqlite3
import subprocess
import sys

from typer.testing import CliRunner

from app.write import app as write_app
from app.logger import system_action_logger
from app.storage_manager import storage_manager
from cortexlog.cli.commands import app
from cortexlog.db.database import database_manager


runner = CliRunner()
write_runner = CliRunner()


def configure_paths(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database_manager, "db_path", tmp_path / "database" / "cortexlog.db")
    monkeypatch.setattr(storage_manager, "logs_root", tmp_path / "logs")
    monkeypatch.setattr(system_action_logger, "log_file", tmp_path / "logs" / "system" / "system_log.txt")


def test_write_saves_enhanced_entry_with_detected_category(tmp_path, monkeypatch) -> None:
    configure_paths(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "write",
            "Today was a hard day at work but I learned a lot.",
            "--title",
            "diary",
            "--mode",
            "professional",
        ],
        input="2\n",
    )

    assert result.exit_code == 0
    assert "Detected category: Diary" in result.stdout
    assert "Saved Diary entry as enhanced." in result.stdout

    saved_files = list((tmp_path / "logs" / "diary").glob("*.txt"))
    assert len(saved_files) == 1
    saved_content = saved_files[0].read_text(encoding="utf-8")
    assert "## Enhanced Text" in saved_content
    assert "## Original Text" not in saved_content
    assert "Today was a hard day at work" not in saved_content

    with sqlite3.connect(tmp_path / "database" / "cortexlog.db") as conn:
        row = conn.execute(
            "SELECT category, final_version_saved, status FROM entries"
        ).fetchone()
    assert row == ("diary", "enhanced", "saved")


def test_write_cancel_does_not_persist_entry(tmp_path, monkeypatch) -> None:
    configure_paths(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["write", "Remember to submit the report tomorrow", "--mode", "technical"],
        input="5\n",
    )

    assert result.exit_code == 0
    assert "Entry cancelled. Nothing was saved." in result.stdout
    assert list((tmp_path / "logs" / "tasks").glob("*.txt")) == []

    with sqlite3.connect(tmp_path / "database" / "cortexlog.db") as conn:
        count = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    assert count == 0

    log_text = (tmp_path / "logs" / "system" / "system_log.txt").read_text(encoding="utf-8")
    assert "action=cancel" in log_text


def test_write_edit_again_uses_updated_text(tmp_path, monkeypatch) -> None:
    configure_paths(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["write", "rough first draft", "--title", "idea"],
        input="4\nIdea title\nA cleaner product concept for team planning\n3\n",
    )

    assert result.exit_code == 0
    assert "Saved Idea entry as both." in result.stdout

    saved_files = list((tmp_path / "logs" / "ideas").glob("*.txt"))
    assert len(saved_files) == 1
    saved_content = saved_files[0].read_text(encoding="utf-8")
    assert "Idea title" in saved_content
    assert "## Original Text" in saved_content
    assert "## Enhanced Text" in saved_content
    assert "Idea: a cleaner product concept for team planning." in saved_content


def test_standalone_app_write_command_works(tmp_path, monkeypatch) -> None:
    configure_paths(tmp_path, monkeypatch)

    result = write_runner.invoke(
        write_app,
        ["hello this note needs cleanup", "--title", "note", "--mode", "professional"],
        input="2\n",
    )

    assert result.exit_code == 0
    assert "Detected category: Note" in result.stdout
    assert list((tmp_path / "logs" / "notes").glob("*.txt"))


def test_python_m_write_module_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "write", "Quick test entry", "--title", "note", "--mode", "professional"],
        input="5\n",
        text=True,
        capture_output=True,
        cwd="/Users/CortexLog",
        check=False,
    )

    assert result.returncode == 0
    assert "Detected category: Note" in result.stdout
    assert "Entry cancelled. Nothing was saved." in result.stdout

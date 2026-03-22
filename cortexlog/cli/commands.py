from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import typer

from cortexlog.ai.processor import AIValidationError, ai_processor
from cortexlog.db.database import database_manager
from cortexlog.services.events_service import events_service
from cortexlog.services.notes_service import notes_service
from cortexlog.services.tasks_service import tasks_service
from cortexlog.utils.datetime_parser import format_human_datetime


LOG_FILE = Path(__file__).resolve().parents[2] / "cortexlog.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)

app = typer.Typer(
    name="cortexlog",
    help="Capture free-form thoughts and turn them into notes, tasks, and events.",
    no_args_is_help=True,
)


@app.callback()
def bootstrap() -> None:
    database_manager.initialize()


@app.command()
def write(text: str) -> None:
    """Write a free-form entry and let AI extract structured items."""
    try:
        result = ai_processor.process_text(text)
    except (RuntimeError, AIValidationError) as exc:
        typer.secho(f"Unable to process entry: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    typer.secho(
        (
            f"Entry processed successfully via {result.source}. "
            f"Created {len(result.notes)} note(s), "
            f"{len(result.tasks)} task(s), and "
            f"{len(result.events)} event(s)."
        ),
        fg=typer.colors.GREEN,
    )


@app.command()
def tasks() -> None:
    """Show all open tasks."""
    open_tasks = tasks_service.get_tasks()
    if not open_tasks:
        typer.echo("No open tasks.")
        return

    typer.echo("Open Tasks")
    typer.echo("-" * 40)
    for task in open_tasks:
        typer.echo(f"[{task.id}] {task.content}")
        typer.echo(f"Due: {format_human_datetime(task.due_date)}")


@app.command()
def today() -> None:
    """Show today's tasks and events."""
    today_items = events_service.get_today()

    typer.echo("Today's Tasks")
    typer.echo("-" * 40)
    if today_items.tasks:
        for task in today_items.tasks:
            typer.echo(f"[{task.id}] {task.content} ({format_human_datetime(task.due_date)})")
    else:
        typer.echo("No tasks due today.")

    typer.echo("")
    typer.echo("Today's Events")
    typer.echo("-" * 40)
    if today_items.events:
        for event in today_items.events:
            typer.echo(f"[{event.id}] {event.title} ({format_human_datetime(event.event_time)})")
    else:
        typer.echo("No events scheduled today.")


@app.command()
def notes(limit: int = 10) -> None:
    """Show recent notes."""
    recent_notes = notes_service.get_notes(limit=limit)
    if not recent_notes:
        typer.echo("No notes found.")
        return

    typer.echo("Recent Notes")
    typer.echo("-" * 40)
    for note in recent_notes:
        typer.echo(f"[{note.id}] {note.content}")
        typer.echo(f"Created: {format_human_datetime(note.created_at)}")


@app.command("export-csv")
def export_csv(output_dir: str = "exports") -> None:
    """Export all app data tables to CSV files."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    export_dir = Path(output_dir) / f"cortexlog-export-{timestamp}"

    exported_files = {
        "notes": database_manager.export_table_to_csv("notes", export_dir / "notes.csv"),
        "tasks": database_manager.export_table_to_csv("tasks", export_dir / "tasks.csv"),
        "events": database_manager.export_table_to_csv("events", export_dir / "events.csv"),
        "raw_logs": database_manager.export_table_to_csv("raw_logs", export_dir / "raw_logs.csv"),
    }

    typer.secho(f"Exported CSV files to {export_dir}", fg=typer.colors.GREEN)
    for label, file_path in exported_files.items():
        typer.echo(f"{label}: {file_path}")

from __future__ import annotations

import typer

from app.confirmation_prompt import EntryPreview, confirmation_prompt
from app.intent_classifier import intent_classifier
from app.logger import system_action_logger
from app.storage_manager import storage_manager
from app.text_enhancer import SUPPORTED_MODES, text_enhancer
from cortexlog.db.database import database_manager


app = typer.Typer(
    add_completion=False,
    help="Standalone entry writer for CortexLog.",
)


def run_write_flow(
    text: str,
    title: str = "",
    mode: str = "professional",
) -> None:
    database_manager.initialize()
    storage_manager.initialize()

    normalized_mode = mode.strip().lower()
    if normalized_mode not in SUPPORTED_MODES:
        typer.secho(
            f"Unsupported mode '{mode}'. Choose from: {', '.join(sorted(SUPPORTED_MODES))}.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    current_title = title.strip()
    current_text = text.strip()

    while True:
        intent = intent_classifier.classify(current_title, current_text)
        enhanced = text_enhancer.enhance_text(
            text=current_text,
            category=intent.key,
            mode=normalized_mode,
        )
        preview = EntryPreview(
            category_label=intent.label,
            title=current_title or _derive_title(current_text, intent.label),
            original_text=current_text,
            enhanced_text=enhanced.text,
            mode=normalized_mode,
        )
        choice = confirmation_prompt.ask(preview)

        if choice == "edit":
            current_title = typer.prompt("Update title", default=preview.title).strip()
            current_text = typer.prompt("Update text", default=current_text).strip()
            continue

        if choice == "cancel":
            system_action_logger.log_action("cancel", intent.key, preview.title, "cancel")
            typer.secho("Entry cancelled. Nothing was saved.", fg=typer.colors.YELLOW)
            return

        saved = storage_manager.save_entry(
            category=intent.key,
            title=preview.title,
            original_text=current_text,
            enhanced_text=enhanced.text,
            final_version_saved=choice,
            tags=intent.tags,
        )
        system_action_logger.log_action("create", intent.key, preview.title, choice)
        typer.secho(f"Saved {intent.label} entry as {choice}. File: {saved.file_path}", fg=typer.colors.GREEN)
        return


@app.command()
def main(
    text: str,
    title: str = typer.Option("", "--title", "-t"),
    mode: str = typer.Option("professional", "--mode", "-m"),
) -> None:
    run_write_flow(text=text, title=title, mode=mode)


def _derive_title(text: str, fallback_label: str) -> str:
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    shortened = first_line[:60].strip()
    return shortened or f"{fallback_label} Entry"


if __name__ == "__main__":
    app()

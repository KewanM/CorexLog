from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import typer


SaveChoice = Literal["original", "enhanced", "both", "edit", "cancel"]


@dataclass(frozen=True)
class EntryPreview:
    category_label: str
    title: str
    original_text: str
    enhanced_text: str
    mode: str


class ConfirmationPrompt:
    CHOICE_MAP: dict[str, SaveChoice] = {
        "1": "original",
        "2": "enhanced",
        "3": "both",
        "4": "edit",
        "5": "cancel",
    }

    def ask(self, preview: EntryPreview) -> SaveChoice:
        typer.echo(f"Detected category: {preview.category_label}")
        if preview.title:
            typer.echo(f"Title: {preview.title}")
        typer.echo(f"Enhancement mode: {preview.mode.title()}")
        typer.echo("")
        typer.echo("Original text:")
        typer.echo(preview.original_text)
        typer.echo("")
        typer.echo("Enhanced version:")
        typer.echo(preview.enhanced_text)
        typer.echo("")
        typer.echo("Do you want to save this entry?")
        typer.echo("[1] Save original only")
        typer.echo("[2] Save enhanced version")
        typer.echo("[3] Save both")
        typer.echo("[4] Edit again")
        typer.echo("[5] Cancel")

        while True:
            choice = typer.prompt("Select an option", default="3").strip()
            mapped = self.CHOICE_MAP.get(choice)
            if mapped is not None:
                return mapped
            typer.secho("Please choose 1, 2, 3, 4, or 5.", fg=typer.colors.YELLOW)


confirmation_prompt = ConfirmationPrompt()

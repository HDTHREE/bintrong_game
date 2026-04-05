import html
import random
from pathlib import Path
import typing_extensions as tp

import genanki
from pydantic import BaseModel, Field, model_validator


class GeneratedFlashcard(BaseModel):
    """Structured generation payload returned by the inference service."""

    front: str = Field(description="Prompt shown on the front of the card.")
    back: str = Field(description="Answer shown on the back of the card.")
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_required_fields(self: tp.Self) -> "GeneratedFlashcard":
        if not self.front.strip(): # pylint: disable=no-member
            raise ValueError("front must not be empty")
        if not self.back.strip(): # pylint: disable=no-member
            raise ValueError("back must not be empty")
        return self

    def to_note_fields(self) -> list[str]:
        return [_format_field(self.front), _format_field(self.back)]


def build_anki_package(
    flashcards: tp.Sequence[GeneratedFlashcard], deck_name: str, output_path: str | Path
) -> None:
    """Create an .apkg file from structured flashcards using genanki."""
    deck = genanki.Deck(_random_anki_id(), deck_name)

    for index, flashcard in enumerate(flashcards):
        fields = flashcard.to_note_fields()
        note = genanki.Note(
            model=genanki.BASIC_AND_REVERSED_CARD_MODEL,
            fields=fields,
            tags=_sanitize_tags(flashcard.tags),
            guid=genanki.guid_for(deck.deck_id, index, *fields),
        )
        deck.add_note(note)

    genanki.Package(deck).write_to_file(str(output_path))


def _sanitize_tags(tags: list[str]) -> list[str]:
    """Sanitize LLM-generated tags for genanki: replace spaces with underscores and drop empties."""
    sanitized = []
    for tag in tags:
        clean = tag.strip().replace(" ", "_")
        if clean:
            sanitized.append(clean)
    return sanitized


def _format_field(value: str | None) -> str:
    if value is None:
        return ""
    return html.escape(value.strip()).replace("\n", "<br>")


def _random_anki_id() -> int:
    return random.randrange(1 << 30, 1 << 31)

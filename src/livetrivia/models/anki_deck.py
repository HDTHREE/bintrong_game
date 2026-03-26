import html
import random
from enum import StrEnum
from pathlib import Path
import typing_extensions as tp

import genanki
from pydantic import BaseModel, Field, model_validator


class FlashcardModelName(StrEnum):
    BASIC_MODEL = "BASIC_MODEL"
    BASIC_AND_REVERSED_CARD_MODEL = "BASIC_AND_REVERSED_CARD_MODEL"
    BASIC_OPTIONAL_REVERSED_CARD_MODEL = "BASIC_OPTIONAL_REVERSED_CARD_MODEL"
    BASIC_TYPE_IN_THE_ANSWER_MODEL = "BASIC_TYPE_IN_THE_ANSWER_MODEL"
    CLOZE_MODEL = "CLOZE_MODEL"


GENANKI_MODEL_BY_NAME: dict[FlashcardModelName, genanki.Model] = {
    FlashcardModelName.BASIC_MODEL: genanki.BASIC_MODEL,
    FlashcardModelName.BASIC_AND_REVERSED_CARD_MODEL: genanki.BASIC_AND_REVERSED_CARD_MODEL,
    FlashcardModelName.BASIC_OPTIONAL_REVERSED_CARD_MODEL: genanki.BASIC_OPTIONAL_REVERSED_CARD_MODEL,
    FlashcardModelName.BASIC_TYPE_IN_THE_ANSWER_MODEL: genanki.BASIC_TYPE_IN_THE_ANSWER_MODEL,
    FlashcardModelName.CLOZE_MODEL: genanki.CLOZE_MODEL,
}


class GeneratedFlashcard(BaseModel):
    """Structured generation payload returned by the inference service."""

    model_name: FlashcardModelName
    front: str | None = Field(
        default=None,
        description="Prompt shown on the front for non-cloze cards.",
    )
    back: str | None = Field(
        default=None,
        description="Answer shown on the back for non-cloze cards.",
    )
    add_reverse: bool = Field(
        default=False,
        description="Whether the optional reversed model should create the reverse card.",
    )
    text: str | None = Field(
        default=None,
        description="Cloze text containing one or more {{cN::...}} deletions.",
    )
    back_extra: str = Field(
        default="",
        description="Extra explanation shown on the back of cloze cards.",
    )
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_required_fields(self) -> tp.Self:
        data = self.model_dump()
        text = data.get("text")
        front = data.get("front")
        back = data.get("back")

        if self.model_name == FlashcardModelName.CLOZE_MODEL:
            if not isinstance(text, str) or not text.strip():
                raise ValueError("CLOZE_MODEL requires text")
            return self

        if not isinstance(front, str) or not front.strip():
            raise ValueError(f"{self.model_name} requires front")
        if not isinstance(back, str) or not back.strip():
            raise ValueError(f"{self.model_name} requires back")
        return self

    @property
    def genanki_model(self) -> genanki.Model:
        return GENANKI_MODEL_BY_NAME[self.model_name]

    def to_note_fields(self) -> list[str]:
        if self.model_name == FlashcardModelName.BASIC_MODEL:
            return [_format_field(self.front), _format_field(self.back)]
        if self.model_name == FlashcardModelName.BASIC_AND_REVERSED_CARD_MODEL:
            return [_format_field(self.front), _format_field(self.back)]
        if self.model_name == FlashcardModelName.BASIC_OPTIONAL_REVERSED_CARD_MODEL:
            add_reverse = "y" if self.add_reverse else ""
            return [_format_field(self.front), _format_field(self.back), add_reverse]
        if self.model_name == FlashcardModelName.BASIC_TYPE_IN_THE_ANSWER_MODEL:
            return [_format_field(self.front), _format_field(self.back)]
        return [_format_field(self.text), _format_field(self.back_extra)]


def build_anki_package(
    flashcards: tp.Sequence[GeneratedFlashcard], deck_name: str, output_path: str | Path
) -> None:
    """Create an .apkg file from structured flashcards using genanki."""
    deck = genanki.Deck(_random_anki_id(), deck_name)

    for index, flashcard in enumerate(flashcards):
        fields = flashcard.to_note_fields()
        note = genanki.Note(
            model=flashcard.genanki_model,
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

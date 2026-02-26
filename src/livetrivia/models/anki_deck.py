"""SQLModel models for Anki collection.anki2 database. Table definitions adapted from: https://github.com/kerrickstaley/genanki/blob/main/genanki/apkg_schema.py."""

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode, JsonSchemaValue
from sqlalchemy import Index
from sqlmodel import SQLModel, Field
import typing_extensions as tp


if tp.TYPE_CHECKING:
    import sqlalchemy as sqla
    import sqlalchemy.ext.asyncio.session as sqlas
    from pydantic_core.core_schema import CoreSchema


class Col(SQLModel, table=True):
    """Collection metadata table.

    Stores global collection configuration including models, decks, and settings.
    There is typically only one row in this table.
    """

    __tablename__ = "col"

    id: int = Field(default=None, primary_key=True)
    crt: int = Field(description="Creation timestamp (seconds since epoch)")
    mod: int = Field(description="Last modified timestamp (milliseconds since epoch)")
    scm: int = Field(description="Schema modification time (milliseconds since epoch)")
    ver: int = Field(description="Schema version")
    dty: int = Field(description="Dirty flag (unused in modern Anki)")
    usn: int = Field(description="Update sequence number for syncing")
    ls: int = Field(description="Last sync time (milliseconds since epoch)")
    conf: str = Field(description="JSON object of collection configuration")
    models: str = Field(description="JSON object of note types (models)")
    decks: str = Field(description="JSON object of decks")
    dconf: str = Field(description="JSON object of deck configurations")
    tags: str = Field(description="JSON object of tags cache")


class Note(SQLModel, table=True):
    """Notes table.

    A note is the source content from which cards are generated.
    Each note has fields that are rendered into cards via templates.
    """

    __tablename__ = "notes"
    __table_args__ = (
        Index("ix_notes_usn", "usn"),
        Index("ix_notes_csum", "csum"),
    )

    id: int = Field(
        default=None, primary_key=True, description="Note ID (epoch milliseconds)"
    )
    guid: str = Field(description="Globally unique ID for syncing")
    mid: int = Field(description="Model (note type) ID")
    mod: int = Field(description="Modification timestamp (seconds since epoch)")
    usn: int = Field(description="Update sequence number for syncing")
    tags: str = Field(default="", description="Space-separated list of tags")
    flds: str = Field(description="Fields separated by \\x1f (unit separator)")
    sfld: str = Field(description="Sort field for searching/sorting")
    csum: int = Field(description="Checksum of first field for duplicate detection")
    flags: int = Field(default=0, description="Unused flags")
    data: str = Field(default="", description="Unused data field")


class Card(SQLModel, table=True):
    """Cards table.

    A card is a specific flashcard generated from a note.
    Each note can produce multiple cards based on its templates.
    """

    __tablename__ = "cards"
    __table_args__ = (
        Index("ix_cards_usn", "usn"),
        Index("ix_cards_nid", "nid"),
        Index("ix_cards_sched", "did", "queue", "due"),
    )

    id: int = Field(
        default=None, primary_key=True, description="Card ID (epoch milliseconds)"
    )
    nid: int = Field(description="Note ID this card belongs to")
    did: int = Field(description="Deck ID this card belongs to")
    ord: int = Field(
        description="Template ordinal (which template generated this card)"
    )
    mod: int = Field(description="Modification timestamp (seconds since epoch)")
    usn: int = Field(description="Update sequence number for syncing")
    type: int = Field(
        default=0, description="Card type: 0=new, 1=learning, 2=review, 3=relearning"
    )
    queue: int = Field(
        default=0,
        description="Queue: -3=sched buried, -2=user buried, -1=suspended, 0=new, 1=learning, 2=review, 3=day learning, 4=preview",
    )
    due: int = Field(description="Due date/position (meaning depends on queue)")
    ivl: int = Field(
        default=0, description="Current interval in days (negative = seconds)"
    )
    factor: int = Field(
        default=0, description="Ease factor (per mille, e.g., 2500 = 250%)"
    )
    reps: int = Field(default=0, description="Number of reviews")
    lapses: int = Field(
        default=0, description="Number of times card went from review to relearning"
    )
    left: int = Field(default=0, description="Remaining learning/relearning steps")
    odue: int = Field(default=0, description="Original due date (for filtered decks)")
    odid: int = Field(default=0, description="Original deck ID (for filtered decks)")
    flags: int = Field(default=0, description="Card flags (colors)")
    data: str = Field(default="", description="Unused data field")


class RevLog(SQLModel, table=True):
    """Review log table.

    Records each review of a card for statistics and undo functionality.
    """

    __tablename__ = "revlog"
    __table_args__ = (
        Index("ix_revlog_usn", "usn"),
        Index("ix_revlog_cid", "cid"),
    )

    id: int = Field(
        default=None,
        primary_key=True,
        description="Review timestamp (epoch milliseconds)",
    )
    cid: int = Field(description="Card ID reviewed")
    usn: int = Field(description="Update sequence number for syncing")
    ease: int = Field(description="Button pressed: 1=again, 2=hard, 3=good, 4=easy")
    ivl: int = Field(description="New interval after review (negative = seconds)")
    lastIvl: int = Field(description="Previous interval before review")
    factor: int = Field(description="New ease factor after review")
    time: int = Field(description="Review duration in milliseconds")
    type: int = Field(
        description="Review type: 0=learn, 1=review, 2=relearn, 3=cram/filtered, 4=manual"
    )


class Grave(SQLModel, table=True):
    """Graves table.

    Records deleted cards, notes, and decks for syncing purposes.
    """

    __tablename__ = "graves"

    usn: int = Field(primary_key=True, description="Update sequence number")
    oid: int = Field(primary_key=True, description="Original ID of deleted object")
    type: int = Field(primary_key=True, description="Type: 0=card, 1=note, 2=deck")


class AnkiCollection(BaseModel):
    col: Col
    notes: list[Note]
    cards: list[Card]

    revlog: list[RevLog] = Field(default_factory=list)

    graves: list[Grave] = Field(default_factory=list)

    async def add_to_sql(
        self: tp.Self, engine: "sqlas.AsyncSession", commit: bool = True
    ) -> None:
        engine.add(self.col)
        for note in self.notes:
            engine.add(note)
        for card in self.cards:
            engine.add(card)
        for revlog_entry in self.revlog:
            engine.add(revlog_entry)
        for grave in self.graves:
            engine.add(grave)
        if commit:
            await engine.commit()

    @classmethod
    def merge(cls, *collections: "AnkiCollection") -> "AnkiCollection":
        """
        Merge one or more AnkiCollection objects into a new AnkiCollection, remapping IDs to avoid collisions.
        """
        if not collections:
            raise ValueError("At least one AnkiCollection must be provided")

        import time

        main_col = collections[0].col
        all_notes = []
        all_cards = []
        all_revlog = []
        all_graves = []

        base_id = int(time.time() * 1000)
        counter = 0

        for partial in collections:
            note_id_map = {}
            card_id_map = {}

            for note in partial.notes:
                old_id = note.id
                new_id = base_id + counter
                counter += 1
                note.id = new_id
                note.mod = int(time.time())
                note_id_map[old_id] = new_id
                all_notes.append(note)

            for card in partial.cards:
                old_card_id = card.id
                new_card_id = base_id + counter
                counter += 1
                card.id = new_card_id
                card.nid = note_id_map.get(card.nid, card.nid)
                card.mod = int(time.time())
                card_id_map[old_card_id] = new_id
                all_cards.append(card)

            for rev in partial.revlog:
                rev.cid = card_id_map.get(rev.cid, rev.cid)
                all_revlog.append(rev)

            all_graves.extend(partial.graves)

        return cls(
            col=main_col,
            notes=all_notes,
            cards=all_cards,
            revlog=all_revlog,
            graves=all_graves,
        )


def create_anki_tables(engine: "sqla.Connection") -> None:
    """Create all Anki collection tables in the database."""
    SQLModel.metadata.create_all(
        engine,
        tables=[
            Col.__table__,
            Note.__table__,
            Card.__table__,
            RevLog.__table__,
            Grave.__table__,
        ],
        checkfirst=False,
    )

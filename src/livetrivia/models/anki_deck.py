"""SQLModel models for Anki collection.anki2 database."""

from pydantic import BaseModel, Field
from sqlmodel import SQLModel, Field
import sqlalchemy.ext.asyncio.session as sqlas
import typing_extensions as tp


if tp.TYPE_CHECKING:
    import sqlalchemy.connectors as sqlcon


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

    id: int = Field(default=None, primary_key=True, description="Note ID (epoch milliseconds)")
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

    id: int = Field(default=None, primary_key=True, description="Card ID (epoch milliseconds)")
    nid: int = Field(description="Note ID this card belongs to")
    did: int = Field(description="Deck ID this card belongs to")
    ord: int = Field(description="Template ordinal (which template generated this card)")
    mod: int = Field(description="Modification timestamp (seconds since epoch)")
    usn: int = Field(description="Update sequence number for syncing")
    type: int = Field(default=0, description="Card type: 0=new, 1=learning, 2=review, 3=relearning")
    queue: int = Field(default=0, description="Queue: -3=sched buried, -2=user buried, -1=suspended, 0=new, 1=learning, 2=review, 3=day learning, 4=preview")
    due: int = Field(description="Due date/position (meaning depends on queue)")
    ivl: int = Field(default=0, description="Current interval in days (negative = seconds)")
    factor: int = Field(default=0, description="Ease factor (per mille, e.g., 2500 = 250%)")
    reps: int = Field(default=0, description="Number of reviews")
    lapses: int = Field(default=0, description="Number of times card went from review to relearning")
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

    id: int = Field(default=None, primary_key=True, description="Review timestamp (epoch milliseconds)")
    cid: int = Field(description="Card ID reviewed")
    usn: int = Field(description="Update sequence number for syncing")
    ease: int = Field(description="Button pressed: 1=again, 2=hard, 3=good, 4=easy")
    ivl: int = Field(description="New interval after review (negative = seconds)")
    lastIvl: int = Field(description="Previous interval before review")
    factor: int = Field(description="New ease factor after review")
    time: int = Field(description="Review duration in milliseconds")
    type: int = Field(description="Review type: 0=learn, 1=review, 2=relearn, 3=cram/filtered, 4=manual")


class Grave(SQLModel, table=True):
    """Graves table.

    Records deleted cards, notes, and decks for syncing purposes.
    """

    __tablename__ = "graves"

    usn: int = Field(primary_key=True, description="Update sequence number")
    oid: int = Field(primary_key=True, description="Original ID of deleted object")
    type: int = Field(primary_key=True, description="Type: 0=card, 1=note, 2=deck")


class AnkiModel(BaseModel):
    col: Col
    notes: list[Note]
    cards: list[Card]

    revlog: list[RevLog] = Field(default_factory=list)
    """OMIT."""

    graves: list[Grave] = Field(default_factory=list)
    """OMIT."""

    async def add_to_sql(self, engine: "sqlas.AsyncSession", commit: bool = True) -> None:
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


async def create_anki_tables(engine: "sqlas.AsyncSession") -> None:
    """Create all Anki collection tables in the database."""
    SQLModel.metadata.create_all(engine, tables=[Col, Note, Card, RevLog, Grave], checkfirst=False)

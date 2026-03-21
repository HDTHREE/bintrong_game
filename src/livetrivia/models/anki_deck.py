"""SQLModel models for Anki collection.anki2 database. Table definitions adapted from: https://github.com/kerrickstaley/genanki/blob/main/genanki/apkg_schema.py."""

import json

from pydantic import BaseModel
from sqlalchemy import Index
from sqlmodel import SQLModel, Field
import time
import typing_extensions as tp


if tp.TYPE_CHECKING:
    import sqlalchemy as sqla
    import sqlalchemy.ext.asyncio.session as sqlas


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
    ver: int = Field(description="Schema version", ge=11, le=20)
    dty: int = Field(description="Dirty flag (unused in modern Anki)", ge=0, le=1)
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
    csum: int = Field(
        description="Checksum of first field for duplicate detection",
        ge=0,
        le=2**31 - 1,
    )
    flags: int = Field(default=0, description="Unused flags", ge=0)
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
        default=0,
        ge=0,
        le=3,
        description="Card type: 0=new, 1=learning, 2=review, 3=relearning",
    )
    queue: int = Field(
        default=0,
        ge=-3,
        le=4,
        description="Queue: -3=sched buried, -2=user buried, -1=suspended, 0=new, 1=learning, 2=review, 3=day learning, 4=preview",
    )
    due: int = Field(description="Due date/position (meaning depends on queue)")
    ivl: int = Field(
        default=0,
        ge=-999999,
        le=999999,
        description="Current interval in days (negative = seconds)",
    )
    factor: int = Field(
        default=0,
        description="Ease factor (per mille, e.g., 2500 = 250%)",
        ge=0,
        le=9999,
    )
    reps: int = Field(default=0, description="Number of reviews", ge=0)
    lapses: int = Field(
        default=0,
        description="Number of times card went from review to relearning",
        ge=0,
    )
    left: int = Field(
        default=0, description="Remaining learning/relearning steps", ge=0
    )
    odue: int = Field(default=0, description="Original due date (for filtered decks)")
    odid: int = Field(default=0, description="Original deck ID (for filtered decks)")
    flags: int = Field(default=0, description="Card flags (colors)", ge=0)
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
    ease: int = Field(
        description="Button pressed: 1=again, 2=hard, 3=good, 4=easy", ge=1, le=4
    )
    ivl: int = Field(
        description="New interval after review (negative = seconds)",
        ge=-999999,
        le=999999,
    )
    lastIvl: int = Field(description="Previous interval before review")
    factor: int = Field(description="New ease factor after review", ge=0, le=9999)
    time: int = Field(description="Review duration in milliseconds", ge=0)
    type: int = Field(
        description="Review type: 0=learn, 1=review, 2=relearn, 3=cram/filtered, 4=manual",
        ge=0,
        le=4,
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
        self.col.ver = 11
        if not self.col.conf or not self._is_valid_json(self.col.conf):
            self.col.conf = json.dumps(
                {
                    "curDeck": 1,
                    "activeDecks": [1],
                    "newSpread": 0,
                    "collapseTime": 1200,
                    "timeLim": 600,
                    "estTimes": True,
                    "dueCounts": True,
                    "curModel": "1",
                    "nextPos": 1,
                    "sortType": "noteFld",
                    "sortBackwards": False,
                    "addToCur": True,
                    "dayLearnFirst": False,
                    "newBury": True,
                }
            )
        if not self.col.models or not self._is_valid_json(self.col.models):
            tmpls = [
                {
                    "name": "Card 1",
                    "qfmt": "{{Front}}",
                    "afmt": "{{Back}}",
                    "bafmt": "",
                    "bqfmt": "",
                    "did": None,
                    "ord": 0,
                }
            ]
            flds = [
                {
                    "name": "Front",
                    "sticky": False,
                    "font": "Arial",
                    "media": [],
                    "ord": 0,
                    "rtl": False,
                    "size": 20,
                }
            ]
            self.col.models = json.dumps(
                {
                    "1": {
                        "css": ".card { font-family: arial; font-size: 20px; color: black; background-color: white; }",
                        "did": 1,
                        "flds": flds,
                        "id": 1,
                        "latexPost": "\\end{document}",
                        "latexPre": "\\documentclass[12pt]{article}\\special{papersize=3in,5in}\\usepackage[utf8]{inputenc}\\usepackage{amssymb,amsmath}\\pagestyle{empty}",
                        "mod": 0,
                        "name": "Basic",
                        "req": [[0, "all", [0]]],
                        "sortf": 0,
                        "tags": [],
                        "tmpls": tmpls,
                        "type": 0,
                        "usn": 0,
                        "vers": [],
                    }
                }
            )
        if not self.col.decks or not self._is_valid_json(self.col.decks):
            self.col.decks = json.dumps(
                {
                    "1": {
                        "name": "Default",
                        "id": 1,
                        "mod": 0,
                        "usn": 0,
                        "desc": "",
                        "dyn": 0,
                        "collapsed": False,
                        "browserCollapsed": False,
                        "extendRev": 10,
                        "extendNew": 10,
                        "conf": 1,
                        "revToday": [0, 0],
                        "newToday": [0, 0],
                        "lrnToday": [0, 0],
                        "timeToday": [0, 0],
                        "md": False,
                    }
                }
            )
        if not self.col.dconf or not self._is_valid_json(self.col.dconf):
            self.col.dconf = json.dumps(
                {
                    "1": {
                        "name": "Default",
                        "replayq": True,
                        "lapse": {
                            "delays": [10],
                            "leechFails": 8,
                            "minInt": 1,
                            "mult": 0.0,
                            "leechAction": 0,
                        },
                        "rev": {
                            "perDay": 100,
                            "fuzz": 0.05,
                            "ivlFct": 1,
                            "maxIvl": 36500,
                            "minSpace": 1,
                            "ease4": 1.3,
                            "bury": True,
                        },
                        "timer": 0,
                        "autoplay": True,
                        "dyn": False,
                        "mod": 0,
                        "usn": 0,
                        "new": {
                            "perDay": 20,
                            "delays": [1, 10],
                            "separate": True,
                            "ints": [1, 4, 7],
                            "initialFactor": 2500,
                            "bury": True,
                            "order": 1,
                        },
                        "maxTaken": 60,
                        "id": 1,
                    }
                }
            )
        if not self.col.tags or not self._is_valid_json(self.col.tags):
            self.col.tags = "{}"
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

    @staticmethod
    def _is_valid_json(val: str) -> bool:
        try:
            parsed = json.loads(val)
            return isinstance(parsed, dict)
        except Exception:
            return False

    @classmethod
    def merge(cls, *collections: "AnkiCollection") -> "AnkiCollection":
        """
        Merge one or more AnkiCollection objects into a new AnkiCollection, remapping IDs to avoid collisions.
        """
        if not collections:
            raise ValueError("At least one AnkiCollection must be provided")

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
    """Create all Anki collection tables."""
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

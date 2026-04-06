from sqlmodel import Field, SQLModel, Relationship
import uuid
from datetime import datetime
import typing_extensions as tp
from livetrivia.models.status import Status

if tp.TYPE_CHECKING:
    from livetrivia.models.game import Game


class Round(SQLModel, table=True):
    """Table for round."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    """Primary key column: No other meaning besides an unique identifier."""

    game_id: uuid.UUID = Field(foreign_key="game.id")
    """Column: Relates a round to the game it was played in."""
    status: Status = Field(default=Status.STARTING)
    """Column: Current status of the round."""
    created_at: datetime = Field(default_factory=datetime.now)
    """Column: Issue time of round."""
    started_at: datetime | None = None
    """Column: Start time of round."""
    ended_at: datetime | None = None
    """Column: End time of round."""
    winner_id: uuid.UUID | None = Field(default=None, foreign_key="gameplayer.id")
    """Column: The GamePlayer that won this round."""

    game: "Game" = Relationship()
    """Related entry: Game that this round was played in."""

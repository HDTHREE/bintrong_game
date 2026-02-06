from sqlmodel import Field, SQLModel, Relationship
import uuid
from datetime import datetime
import typing_extensions as tp
import functools as fnt

from livetrivia.models.status import Status
from livetrivia.utils import generate_random_string

if tp.TYPE_CHECKING:
    from livetrivia.models.session import Session


class Game(SQLModel, table=True):
    """Table for Games."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    """Primary key column: No other meaning besides an unique identifier."""

    host_session_id: uuid.UUID = Field(foreign_key="session.id")
    """Foreign key column: Relates the owner to this entry."""

    game_code: str | None = Field(
        default=fnt.partial(generate_random_string, length=6), unique=True, index=True
    )
    """Column: Random 6 length alphebetic string that currently connects to this game."""
    status: Status = Field(default=Status.STARTING)
    """Column: Current status of the round."""
    created_at: datetime = Field(default_factory=datetime.now)
    """Column: Issue time of game."""
    started_at: datetime | None = None
    """Column: Start time of game."""
    ended_at: datetime | None = None
    """Column: End time of game."""

    host_session: "Session" = Relationship()
    """Related entry: Session of the player hosting."""
    player_sessions: list["GamePlayer"] = Relationship(back_populates="game")
    """Related entries: GamePlayer entries of the player details."""


class GamePlayer(SQLModel, table=True):
    """Table for GamePlayers."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    """Primary key column: No other meaning besides an unique identifier."""

    game_id: uuid.UUID = Field(foreign_key="game.id")
    """Foreign key column: Relates a to game this entry was played in."""
    session_id: uuid.UUID = Field(foreign_key="session.id")
    """Foreign key column: Relates a to the player session that participated in this game."""

    score: int = Field(default=0)
    """Column: The score that a player recived for thier performance."""
    joined_at: datetime = Field(default_factory=datetime.now)
    """Column: The time that a player joined the game first."""
    is_active: bool = Field(default=True)
    """Column: Status of a plyer still being in the game."""

    game: Game = Relationship(back_populates="player_sessions")
    """Related Entry: The game this player was playing in."""
    session: "Session" = Relationship()
    """Related Entry: The session of the player that played."""

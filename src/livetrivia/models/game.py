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
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    host_session_id: uuid.UUID = Field(foreign_key="session.id")

    game_code: str | None = Field(
        default=fnt.partial(generate_random_string, length=6), unique=True, index=True
    )
    status: Status = Field(default=Status.STARTING)

    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    ended_at: datetime | None = None

    host_session: "Session" = Relationship()
    player_sessions: list["GamePlayer"] = Relationship(back_populates="game")


class GamePlayer(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    game_id: uuid.UUID = Field(foreign_key="game.id")
    session_id: uuid.UUID = Field(foreign_key="session.id")

    score: int = Field(default=0)

    joined_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)

    game: Game = Relationship(back_populates="player_sessions")
    session: "Session" = Relationship()

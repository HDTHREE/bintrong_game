from sqlmodel import Field, SQLModel, Relationship
import uuid
from datetime import datetime
import typing_extensions as tp
from livetrivia.models.status import Status

if tp.TYPE_CHECKING:
    from livetrivia.models.game import Game


class Round(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    game_id: uuid.UUID = Field(foreign_key="game.id")

    status: Status = Field(default=Status.STARTING)

    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    ended_at: datetime | None = None

    game: "Game" = Relationship(
        sa_relationship_kwargs={"foreign_keys": ["Round.game_id"]}
    )

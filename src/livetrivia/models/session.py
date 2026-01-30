from sqlmodel import Field, SQLModel, Relationship
from pydantic import computed_field
import uuid
from datetime import datetime
import typing_extensions as tp

if tp.TYPE_CHECKING:
    from livetrivia.models.user import User


class Session(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id")

    access_token: str
    refresh_token: str
    is_active: bool = Field(default=True)

    created_at: datetime = Field(default_factory=datetime.now)

    access_token_expires_at: datetime
    refresh_token_expires_at: datetime

    user: "User" = Relationship(back_populates="sessions")

    @computed_field
    @property
    def is_guest(self) -> bool:
        return self.user_id is None

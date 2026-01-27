from sqlmodel import Field, SQLModel, Relationship
import uuid
from datetime import datetime
import typing_extensions as tp

if tp.TYPE_CHECKING:
    from livetrivia.models.user import User



class Session(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    access_token: str
    refresh_token: str
    created_at: datetime = Field(default_factory=datetime.now)
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    is_active: bool = Field(default=True)

    user: "User" = Relationship(back_populates="sessions")


import typing_extensions as tp
from sqlmodel import Field, SQLModel, Relationship
import uuid
if tp.TYPE_CHECKING:
    from livetrivia.models.user import User


class File(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    prefix: str

    user_id: uuid.UUID = Field(foreign_key="user.id")
    user: "User" = Relationship(back_populates="files")

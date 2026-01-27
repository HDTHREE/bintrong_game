import typing_extensions as tp
from sqlmodel import Field, SQLModel, Relationship
import uuid
from pydantic import EmailStr, BaseModel
if tp.TYPE_CHECKING:
    from livetrivia.models.session import Session
    from livetrivia.models.file import File


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: EmailStr
    password: str

    files: list["File"] = Relationship(back_populates="user")
    sessions: list["Session"] = Relationship(back_populates="user")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

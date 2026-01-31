from pydantic import BaseModel
import typing_extensions as tp
from sqlmodel import Field, SQLModel, Relationship
import uuid

if tp.TYPE_CHECKING:
    from livetrivia.models.user import User


class File(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    generated_from_id: uuid.UUID | None = Field(foreign_key="file.id")

    prefix: str

    user: "User" = Relationship(back_populates="files")


class FileDataResponse(BaseModel):
    id: uuid.UUID
    prefix: str
    user_id: uuid.UUID

    class Config:
        from_attributes = True
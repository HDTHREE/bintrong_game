import typing_extensions as tp
from sqlmodel import Field, SQLModel, create_engine, Relationship
import uuid


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str

    files: list["File"] = Relationship(back_populates="user")


class File(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    prefix: str

    user_id: uuid.UUID = Field(foreign_key="user.id")
    user: "User" = Relationship(back_populates="files")

import typing_extensions as tp
from sqlmodel import Field, SQLModel, Relationship
import uuid
from pydantic import EmailStr, BaseModel

if tp.TYPE_CHECKING:
    from livetrivia.models.session import Session
    from livetrivia.models.files import File


class User(SQLModel, table=True):
    """Table for users."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    """Primary key column: No other meaning besides an unique identifier."""
    email: EmailStr
    """Column: User email string input."""
    password: str
    """Column: User password hash."""

    files: list["File"] = Relationship(back_populates="user")
    """Related entries: Details files owned by user."""
    sessions: list["Session"] = Relationship(back_populates="user")
    """Related entries: Details sessions currently held by the user."""


class LoginRequest(BaseModel):
    """Model for requesting user login and accout creation."""

    email: EmailStr
    """User email string input."""
    password: str
    """User password salt and hash result."""

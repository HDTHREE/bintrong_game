from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, DateTime
from pydantic import computed_field
import uuid
from datetime import datetime, timezone
import typing_extensions as tp

if tp.TYPE_CHECKING:
    from livetrivia.models.user import User


class Session(SQLModel, table=True):
    """Table for sessions."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    """Primary key column: No other meaning besides an unique identifier."""

    user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id")
    """Optional foreign key column: Relates the owner to this entry."""

    access_token: str
    """Column: JWT access token."""
    refresh_token: str
    """Column: JWT refresh token."""
    is_active: bool = Field(default=True)
    """Column: Status to enable/disable this session's permissions."""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    """Column: Issue time of session."""

    access_token_expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    """Column: Expire time of access token."""
    refresh_token_expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True))
    )
    """Column: Expire time of refresh token."""

    user: "User" = Relationship(back_populates="sessions")
    """Related entry: User that owns this file"""

    @computed_field
    @property
    def is_guest(self) -> bool:
        """Computed field property to determine if a user is a guest."""
        return self.user_id is None

from pydantic import BaseModel
import typing_extensions as tp
from sqlmodel import Field, SQLModel, Relationship
import uuid

if tp.TYPE_CHECKING:
    from livetrivia.models.user import User


class File(SQLModel, table=True):
    """Table for file. NOTE A file's bytes may be stored in file or object storage."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    """Primary key column: No other meaning besides an unique identifier."""
    user_id: uuid.UUID = Field(foreign_key="user.id")
    """Foreign key column: Relates the owner to this entry."""
    generated_from_id: uuid.UUID | None = Field(foreign_key="file.id")
    """Foreign key column: File used to generate this. Will only be present if this file is `.anki`."""
    prefix: str = Field(unique=True)
    """Column: Filepath where file contents are located."""

    user: "User" = Relationship(back_populates="files")
    """Related entry: User that owns this file"""


class FileBlob(SQLModel, table=True):
    """Table for storing raw file binary in postgres. Used as an S3 replacement in production."""

    prefix: str = Field(primary_key=True)
    """Primary key column: Object key mirroring the S3 key / file prefix."""
    content_type: str = Field(default="application/octet-stream")
    """Column: MIME type of the stored object."""
    data: bytes = Field(sa_column_kwargs={"nullable": False})
    """Column: Raw binary content of the file."""


class FileDataResponse(BaseModel):
    """Response model for returning information about an uploaded file."""

    id: uuid.UUID
    """Primary key column: No other meaning besides an unique identifier."""
    prefix: str
    """Filepath where file contents are located."""
    user_id: uuid.UUID
    """Relates the owner to this entry."""
    generated_from_id: uuid.UUID | None
    """Foreign key column: File used to generate this."""
    generated_from_prefix: str | None = None
    """File prefix used to generate this."""

    class Config:
        from_attributes = True

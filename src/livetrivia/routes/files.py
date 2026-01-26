from fastapi import APIRouter, Depends, status, UploadFile, File as FormFile
import sqlalchemy.ext.asyncio as sqlas
from pydantic import BaseModel
import uuid

from livetrivia.db import get_async_session
from livetrivia.models.file import File
from livetrivia.models.session import get_current_user

router: APIRouter = APIRouter(prefix="/files", tags=["files"])


class FileResponse(BaseModel):
    id: uuid.UUID
    prefix: str
    user_id: uuid.UUID

    class Config:
        from_attributes = True


@router.post(
    "/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED
)
async def upload_file(
    user_id: uuid.UUID = Depends(get_current_user),
    file: UploadFile = FormFile(...),
    session: sqlas.AsyncSession = Depends(get_async_session),
) -> File:
    """Upload a file. Currently accepts files but doesn't store them."""
    filename: str = file.filename or "unnamed"
    prefix: str = f"{user_id}/uploads/{filename}"

    new_file = File(
        prefix=prefix,
        user_id=user_id,
    )
    # TODO Figure out s3 file storage
    session.add(new_file)
    await session.commit()
    await session.refresh(new_file)

    return new_file

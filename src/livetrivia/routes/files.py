from fastapi import APIRouter, Depends, status, UploadFile, File as FormFile
import uuid

from livetrivia.db import get_sql_session, get_s3_client, BUCKET_NAME
from livetrivia.models.files import File, FileDataResponse
from livetrivia.routes.session import get_current_user
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import typing_extensions as tp
from sqlmodel import select

if tp.TYPE_CHECKING:
    import sqlalchemy.ext.asyncio as sqlas
    import types_aiobotocore_s3 as aiob3t

router: APIRouter = APIRouter(prefix="/files", tags=["files"])


@router.post("/", response_model=FileDataResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    user_id: uuid.UUID = Depends(get_current_user),
    file: UploadFile = FormFile(...),
    sql: "sqlas.AsyncSession" = Depends(get_sql_session),
    s3: "aiob3t.S3Client" = Depends(get_s3_client),
) -> File:
    id: uuid.UUID = uuid.uuid4()
    filename: str = file.filename or "unnamed"
    prefix: str = f"{user_id}/uploads/{id}/{filename}"

    file_content: bytes = await file.read()
    await s3.put_object(
        Bucket=BUCKET_NAME,
        Key=prefix,
        Body=file_content,
        ContentType=file.content_type or "application/octet-stream",
    )

    new_file: File = File(
        id=id,
        prefix=prefix,
        user_id=user_id,
    )
    sql.add(new_file)
    await sql.commit()
    await sql.refresh(new_file)

    return new_file


@router.get("/{file_id}")
async def download_file(
    file_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user),
    sql: "sqlas.AsyncSession" = Depends(get_sql_session),
    s3: "aiob3t.S3Client" = Depends(get_s3_client),
) -> StreamingResponse:
    file = await sql.get(File, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="file not found")
    if file.user_id != user_id:
        raise HTTPException(status_code=403, detail="forbidden")

    key = file.prefix

    try:
        resp = await s3.get_object(Bucket=BUCKET_NAME, Key=key)
    except Exception:
        raise HTTPException(status_code=404, detail="object not found in storage")

    body = resp.get("Body")
    if body is None:
        raise HTTPException(status_code=500, detail="invalid s3 response")

    async def stream_body():
        nonlocal body
        chunk_size: int = 1024 * 64
        while chunk := await body.read(chunk_size):
            yield chunk

    headers = {}
    content_type = resp.get("ContentType") or "application/octet-stream"
    if resp.get("ContentLength") is not None:
        headers["content-length"] = str(resp.get("ContentLength"))
    headers["content-disposition"] = f'attachment; filename="{key.split("/")[-1]}"'

    return StreamingResponse(stream_body(), media_type=content_type, headers=headers)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user),
    sql: "sqlas.AsyncSession" = Depends(get_sql_session),
    s3: "aiob3t.S3Client" = Depends(get_s3_client),
) -> None:
    file = await sql.get(File, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="file not found")
    if file.user_id != user_id:
        raise HTTPException(status_code=403, detail="forbidden")

    key: str = file.prefix

    try:
        await s3.delete_object(Bucket=BUCKET_NAME, Key=key)
    except Exception:
        raise HTTPException(status_code=500, detail="failed to delete from storage")

    await sql.delete(file)
    await sql.commit()


@router.get(
    "/data/{file_id}", response_model=FileDataResponse, status_code=status.HTTP_200_OK
)
async def get_file_data(
    file_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user),
    sql: "sqlas.AsyncSession" = Depends(get_sql_session),
) -> FileDataResponse:
    file = await sql.get(File, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="file not found")
    if file.user_id != user_id:
        raise HTTPException(status_code=403, detail="forbidden")
    return file


@router.get(
    "/data/", response_model=list[FileDataResponse], status_code=status.HTTP_200_OK
)
async def get_all_files_data(
    user_id: uuid.UUID = Depends(get_current_user),
    sql: "sqlas.AsyncSession" = Depends(get_sql_session),
) -> list[FileDataResponse]:
    stmt = select(File).where(File.user_id == user_id)
    result = await sql.execute(stmt)
    files = result.scalars().all()
    return [
        FileDataResponse(id=f.id, prefix=f.prefix, user_id=f.user_id) for f in files
    ]

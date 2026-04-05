from fastapi import APIRouter, status, UploadFile, File as FormFile
import uuid

from livetrivia.db import SqlSession, Storage, BUCKET_NAME
from livetrivia.models.files import File, FileDataResponse
from livetrivia.routes.session import CurrentUserId
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import select

router: APIRouter = APIRouter(prefix="/files", tags=["files"])


@router.post("/", response_model=FileDataResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    user_id: CurrentUserId,
    sql: SqlSession,
    storage: Storage,
    file: UploadFile = FormFile(...),
) -> File:
    fid: uuid.UUID = uuid.uuid4()
    filename: str = file.filename or "unnamed"
    prefix: str = f"{user_id}/uploads/{fid}/{filename}"

    file_content: bytes = await file.read()
    await storage.put_object(
        Bucket=BUCKET_NAME,
        Key=prefix,
        Body=file_content,
        ContentType=file.content_type or "application/octet-stream",
    )

    new_file: File = File(
        id=fid,
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
    user_id: CurrentUserId,
    sql: SqlSession,
    storage: Storage,
) -> StreamingResponse:
    file = await sql.get(File, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="file not found")
    if file.user_id != user_id:
        raise HTTPException(status_code=403, detail="forbidden")

    key = file.prefix

    try:
        resp = await storage.get_object(Bucket=BUCKET_NAME, Key=key)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="object not found in storage") from exc

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
    user_id: CurrentUserId,
    sql: SqlSession,
    storage: Storage,
) -> None:
    file = await sql.get(File, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="file not found")
    if file.user_id != user_id:
        raise HTTPException(status_code=403, detail="forbidden")

    key: str = file.prefix

    try:
        await storage.delete_object(Bucket=BUCKET_NAME, Key=key)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to delete from storage") from exc

    await sql.delete(file)
    await sql.commit()


@router.get(
    "/data/{file_id}", response_model=FileDataResponse, status_code=status.HTTP_200_OK
)
async def get_file_data(
    file_id: uuid.UUID,
    user_id: CurrentUserId,
    sql: SqlSession,
) -> FileDataResponse:
    file = await sql.get(File, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="file not found")
    if file.user_id != user_id:
        raise HTTPException(status_code=403, detail="forbidden")
    generated_from_prefix: str | None = None
    if file.generated_from_id is not None:
        source = await sql.get(File, file.generated_from_id)
        generated_from_prefix = source.prefix if source else None
    return FileDataResponse(
        id=file.id,
        prefix=file.prefix,
        user_id=file.user_id,
        generated_from_id=file.generated_from_id,
        generated_from_prefix=generated_from_prefix,
    )


@router.get(
    "/data/", response_model=list[FileDataResponse], status_code=status.HTTP_200_OK
)
async def get_all_files_data(
    user_id: CurrentUserId,
    sql: SqlSession,
) -> list[FileDataResponse]:
    stmt = select(File).where(File.user_id == user_id)
    result = await sql.execute(stmt)
    files = result.scalars().all()
    prefix_map: dict[uuid.UUID, str] = {f.id: f.prefix for f in files}
    return [
        FileDataResponse(
            id=f.id,
            prefix=f.prefix,
            user_id=f.user_id,
            generated_from_id=f.generated_from_id,
            generated_from_prefix=prefix_map.get(f.generated_from_id) if f.generated_from_id else None,
        )
        for f in files
    ]


@router.get(
    "/anki/", response_model=list[FileDataResponse], status_code=status.HTTP_200_OK
)
async def get_anki_files(
    user_id: CurrentUserId,
    sql: SqlSession,
) -> list[FileDataResponse]:
    stmt = select(File).where(File.user_id == user_id, File.prefix.endswith(".apkg")) # pylint: disable=no-member
    result = await sql.execute(stmt)
    files = result.scalars().all()
    prefix_map: dict[uuid.UUID, str] = {f.id: f.prefix for f in files}
    return [
        FileDataResponse(
            id=f.id,
            prefix=f.prefix,
            user_id=f.user_id,
            generated_from_id=f.generated_from_id,
            generated_from_prefix=prefix_map.get(f.generated_from_id) if f.generated_from_id else None,
        )
        for f in files
    ]

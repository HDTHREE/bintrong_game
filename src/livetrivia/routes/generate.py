import logging
import aiohttp
import io
import json
import zipfile as zf
import typing_extensions as tp
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import select
from livetrivia.models.anki_deck import AnkiCollection
from livetrivia.models.files import FileDataResponse
from livetrivia.routes.session import CurrentUserId
from livetrivia.db import (
    SqlSession,
    S3Client,
    AnkiOrmSession,
    BUCKET_NAME,
)
import uuid
from livetrivia.text_extraction import (
    YOUTUBE_VIDEO_PREFIX,
    YTApi,
    get_docx_text,
    get_pdf_text,
)
from livetrivia.utils import getenvs
from livetrivia.models.files import File
import time
import asyncio

if tp.TYPE_CHECKING:
    from pydantic import ConfigDict
    import sqlalchemy as sqla


logger: logging.Logger = logging.Logger(__name__)
"""Logger for generate module to log failures to."""


SGLANG_URL: str = getenvs(logger=logger)
"""URL to SGLang service."""


router: APIRouter = APIRouter(prefix="/generate", tags=["generate"])


CHUNK_SIZE = 20000


PROMPT = """"""


CLOZE_PROMPT = """"""


class YouTubeBody(BaseModel):
    """Request body for `/api/generate/`. Allows for generation of anki deck based on youtube URL."""

    model_config: "ConfigDict" = {"arbitrary_types_allowed": True}
    """Model config needed to set this class to be mutuable within `get_gen_text`."""

    video: str
    """URL of video. Can include full-url or video id."""

    cloze: bool
    """Whether or not to generate an anki cloze (fill-in-blank)."""

    file_id: uuid.UUID | None = None
    """**OMIT:** Modified inplace within dependency."""


class FileBody(BaseModel):
    """Request body for `/api/generate/`. Allows for generation of anki deck based on existing file object."""

    file_id: uuid.UUID
    cloze: bool

    @property
    def video(self):
        return None


async def get_gen_api(url: str = Depends(lambda: SGLANG_URL)):
    timeout = aiohttp.ClientTimeout(total=300)
    yield aiohttp.ClientSession(base_url=url, timeout=timeout)


async def get_gen_text(
    input: YouTubeBody | FileBody,
    user_id: CurrentUserId,
    yt: YTApi,
    s3: S3Client,
    sql: SqlSession,
) -> str:
    if input.file_id is not None:
        file = await sql.get(File, input.file_id)
        if not file:
            raise HTTPException(status_code=404, detail="file not found")
        if file.user_id != user_id:
            raise HTTPException(status_code=403, detail="forbidden")
        *_, ext = file.prefix.split(".")
        if ext == ".akpg" or ext not in {".docx", ".pdf", ".txt"}:
            raise HTTPException(status_code=422, detail="unprocessable body")

        resp = await s3.get_object(Bucket=BUCKET_NAME, Key=file.prefix)
        file_bytes = await resp["Body"].read()

        # Parse the file based on extension.
        get_text: tp.Callable[[bytes], str] = {
            ".txt": bytes.decode,
            ".pdf": get_pdf_text,
            ".docx": get_docx_text,
        }.get(ext)

        # TODO: cache this step somehow gl.
        text = get_text(file_bytes)

        return text

    # Get youtube script text.
    *_, video_id = input.video.strip().split(YOUTUBE_VIDEO_PREFIX)

    # Use video ID in prefix so we can check for existing transcripts
    script_prefix = f"{user_id}/scripts/{video_id}/transcript.json"

    # Check if transcript already exists in database.
    existing_file = (
        await sql.execute(select(File).where(File.prefix == script_prefix))
    ).scalar_one_or_none()

    if existing_file is not None:
        # Transcript exists, fetch.
        resp = await s3.get_object(Bucket=BUCKET_NAME, Key=script_prefix)
        text = (await resp["Body"].read()).decode("utf-8")
        input.file_id = existing_file.id
        return text

    # Transcript not found, fetch.
    video = yt.fetch(video_id)
    data = video.to_raw_data()
    text = "\n".join(d.get("text", "") for d in data).strip()

    script_id = uuid.uuid4()

    script_file = File(
        id=script_id,
        prefix=script_prefix,
        user_id=user_id,
        generated_from_id=None,
    )

    input.file_id = script_file.id

    await s3.put_object(
        Bucket=BUCKET_NAME,
        Key=script_prefix,
        Body=text.encode("utf-8"),
        ContentType="application/json",
    )

    sql.add(script_file)
    await sql.commit()
    await sql.refresh(script_file)

    return text


GenApi: tp.TypeAlias = tp.Annotated[aiohttp.ClientSession, Depends(get_gen_api)]


GenText: tp.TypeAlias = tp.Annotated[str, Depends(get_gen_text)]


async def generate_partial(gen: GenApi, prompt: str, chunk: str) -> AnkiCollection:
    full_prompt = prompt + chunk

    payload = {
        "text": full_prompt,
        "sampling_params": {
            "temperature": 0.7,
            "max_new_tokens": 26000,
            "json_schema": json.dumps(AnkiCollection.model_json_schema()),
        },
    }

    async with gen.post("/generate", json=payload) as response:
        if response.status != 200:
            error_text = await response.text()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Generation API error: {error_text}",
            )
        result: dict = await response.json()

    generated_content = json.loads(result.get("text"))
    return AnkiCollection.model_validate(generated_content)


@router.post("/", response_model=FileDataResponse, status_code=status.HTTP_201_CREATED)
async def generate_anki(
    input: YouTubeBody | FileBody,
    text: GenText,
    user_id: CurrentUserId,
    sql: SqlSession,
    anki: AnkiOrmSession,
    s3: S3Client,
    gen: GenApi,
) -> File:

    prompt: str = CLOZE_PROMPT if input.cloze else PROMPT

    chunks = tuple(text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE))

    if not len(chunks):
        raise HTTPException(status_code=400, detail="No content to generate")

    tasks = tuple(generate_partial(gen, prompt, chunk) for chunk in chunks)
    partials = await asyncio.gather(*tasks)

    merged: AnkiCollection = AnkiCollection.merge(*partials)

    await merged.add_to_sql(anki)

    buffer: io.BytesIO = io.BytesIO()

    def synchronous_dump(sync_conn: sqla.Connection) -> None:
        nonlocal buffer
        with open(buffer, "w") as file:
            for line in sync_conn.iterdump():
                file.write("%s\n" % line)
        buffer.seek(0)

    async with await anki.connection() as connection:
        await connection.run_sync(synchronous_dump)

    # Create an in-memory zip file with collection.anki2
    with zf.ZipFile(zip_buffer := io.BytesIO(), "w", zf.ZIP_DEFLATED) as bundle:
        bundle.writestr("collection.anki2", buffer.getvalue())
    zip_buffer.seek(0)

    file_id = uuid.uuid4()
    card_type = "cloze" if input.cloze else "basic"
    filename = f"{card_type}_{file_id}.apkg"
    prefix = f"{user_id}/generated/{file_id}/{filename}"

    await s3.put_object(
        Bucket=BUCKET_NAME,
        Key=prefix,
        Body=zip_buffer.getvalue(),
        ContentType="application/zip",
    )

    if input.file_id is None:
        raise HTTPException(404)

    new_file = File(
        id=file_id,
        prefix=prefix,
        user_id=user_id,
        generated_from_id=input.file_id,
    )
    sql.add(new_file)
    await sql.commit()
    await sql.refresh(new_file)

    return new_file

import logging
from pathlib import Path
import tempfile as tf
import aiohttp
import io
import os
import json
import zipfile as zf
import typing_extensions as tp
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select
from livetrivia.models.anki_deck import AnkiCollection
from livetrivia.models.files import FileDataResponse
from livetrivia.routes.session import CurrentUserId
import sqlalchemy as sqla
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
from livetrivia.utils import getenvs, assets_folder
from livetrivia.models.files import File
import asyncio


logger: logging.Logger = logging.Logger(__name__)
"""Logger for generate module to log failures to."""


SGLANG_URL: str = getenvs(logger=logger)
"""URL to SGLang service."""


router: APIRouter = APIRouter(prefix="/generate", tags=["generate"])


CHUNK_SIZE: int = 20000


DEFAULT_NOTETYPE = {
    "id": 1,
    "name": "Basic",
    "mtime_secs": 0,
    "usn": 0,
    "config": json.dumps(
        {
            "name": "Basic",
            "type": 0,
            "fields": [{"name": "Front"}, {"name": "Back"}],
            "templates": [
                {"name": "Card 1", "qfmt": "{{Front}}", "afmt": "{{Back}}"}
            ],
            "css": ".card { font-family: arial; font-size: 20px; color: black; background-color: white; }",
        }
    ),
}

PROMPT: str = (Path(assets_folder) / "prompt.txt").read_text()


CLOZE_PROMPT: str = (Path(assets_folder) / "cloze_prompt.txt").read_text()


class YouTubeBody(BaseModel):
    """Request body for `/api/generate/`. Allows for generation of anki deck based on youtube URL."""

    video: str
    """URL of video. Can include full-url or video id."""

    cloze: bool
    """Whether or not to generate an anki cloze (fill-in-blank)."""

    file_id: uuid.UUID | None = None
    """**OMIT**."""


class FileBody(BaseModel):
    """Request body for `/api/generate/`. Allows for generation of anki deck based on existing file object."""

    file_id: uuid.UUID
    """File ID to use to generate the deck from."""

    cloze: bool
    """Whether or not to generate an anki cloze (fill-in-blank)."""

    @property
    def video(self) -> None:
        """**OMIT**."""
        return None


async def get_gen_api(url: str = Depends(lambda: SGLANG_URL)):
    timeout = aiohttp.ClientTimeout(total=600)
    session = aiohttp.ClientSession(base_url=url, timeout=timeout)
    try:
        yield session
    finally:
        await session.close()


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
        try:
            # Transcript exists, fetch.
            resp = await s3.get_object(Bucket=BUCKET_NAME, Key=script_prefix)
            text = (await resp["Body"].read()).decode("utf-8")
            input.file_id = existing_file.id
        except:  # noqa: E722
            # If we fail we will just go get it.
            pass
        else:
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

    await s3.put_object(
        Bucket=BUCKET_NAME,
        Key=script_prefix,
        Body=text.encode("utf-8"),
        ContentType="application/json",
    )

    if existing_file is not None:
        return text

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

    text = result.get("text")
    try:
        generated_content = json.loads(text)
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}\nRaw text: {text}")
        raise HTTPException(
            status_code=500, detail=f"Malformed JSON from generation API: {e}"
        )
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

    chunks = tuple(text[i : i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE))

    if not len(chunks):
        raise HTTPException(status_code=400, detail="No content to generate")

    tasks = tuple(generate_partial(gen, prompt, chunk) for chunk in chunks)
    partials = await asyncio.gather(*tasks)

    merged: AnkiCollection = AnkiCollection.merge(*partials)
    merged.col.id = 1

    await merged.add_to_sql(anki)

    # stmt = sqla.text("INSERT INTO notetypes (id, name, mtime_secs, usn, config) VALUES (:id, :name, :mtime_secs, :usn, :config)")
    # await anki.execute(stmt, DEFAULT_NOTETYPE)
    # await anki.commit()

    await anki.execute(sqla.text("PRAGMA legacy_file_format = ON"))
    await anki.commit()

    # Create an in-memory zip file with collection.anki2
    with (
        zf.ZipFile(zip_buffer := io.BytesIO(), "w", zf.ZIP_DEFLATED) as bundle,
        tf.NamedTemporaryFile(suffix=".anki2") as tmp,
    ):
        tmp_path: str = os.path.realpath(tmp.name)
        stmt = sqla.text(f'VACUUM INTO "{tmp_path}"')
        await anki.execute(stmt)
        await anki.commit()
        await anki.close()

        bundle.write(tmp_path, "collection.anki2")
        bundle.writestr("media", r"{}")

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
        *_, video_id = input.video.strip().split(YOUTUBE_VIDEO_PREFIX)
        script_prefix = f"{user_id}/scripts/{video_id}/transcript.json"
        if (
            script := (
                await sql.execute(select(File).where(File.prefix == script_prefix))
            ).scalar_one_or_none()
        ) is None:
            raise HTTPException(404)
        input.file_id = script.id

    new_file: File = File(
        id=file_id,
        prefix=prefix,
        user_id=user_id,
        generated_from_id=input.file_id,
    )
    sql.add(new_file)
    await sql.commit()
    await sql.refresh(new_file)

    return new_file

import asyncio
import json
import logging
from pathlib import Path
import tempfile as tf
import typing_extensions as tp
import uuid

import aiohttp
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import select

from livetrivia.db import BUCKET_NAME, Storage, SqlSession
from livetrivia.models.anki_deck import (
    GeneratedFlashcard,
    build_anki_package,
)
from livetrivia.models.files import File, FileDataResponse
from livetrivia.routes.session import CurrentUserId
from livetrivia.text_extraction import (
    YOUTUBE_VIDEO_PREFIX,
    YTApi,
    get_docx_text,
    get_pdf_text,
)
from livetrivia.utils import assets_folder, getenvs


logger: logging.Logger = logging.Logger(__name__)
"""Logger for generate module to log failures to."""


SGLANG_URL: str = getenvs(logger=logger)
"""URL to SGLang service."""


router: APIRouter = APIRouter(prefix="/generate", tags=["generate"])


CHUNK_SIZE: int = 20000

PROMPT: str = (Path(assets_folder) / "prompt.txt").read_text()
REQUIRED_FIELDS_GUIDANCE: str = (
    "Return exactly one JSON object with no markdown. "
    "For model_name='CLOZE_MODEL', include non-empty text (and optional back_extra, tags). "
    "For any non-cloze model_name, include non-empty front and back (and optional add_reverse, tags). "
    "Do not omit required fields."
)
MIXED_PROMPT: str = (
    PROMPT
    + "\n\n"
    + "Return exactly one flashcard as JSON using the provided schema. "
    + "Use a mix of card models across generations, including both CLOZE_MODEL and non-cloze models when appropriate to the content. "
    + REQUIRED_FIELDS_GUIDANCE
)


class YouTubeBody(BaseModel):
    """Request body for `/api/generate/`. Allows for generation of anki deck based on youtube URL."""

    model_config = ConfigDict(extra="forbid")

    video: str
    """URL of video. Can include full-url or video id."""

    file_id: uuid.UUID | None = None
    """**OMIT**."""


class FileBody(BaseModel):
    """Request body for `/api/generate/`. Allows for generation of anki deck based on existing file object."""

    model_config = ConfigDict(extra="forbid")

    file_id: uuid.UUID
    """File ID to use to generate the deck from."""

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
    request: YouTubeBody | FileBody,
    user_id: CurrentUserId,
    yt: YTApi,
    s3: Storage,
    sql: SqlSession,
) -> str:
    if request.file_id is not None:
        file = await sql.get(File, request.file_id)
        if not file:
            raise HTTPException(status_code=404, detail="file not found")
        if file.user_id != user_id:
            raise HTTPException(status_code=403, detail="forbidden")

        ext = Path(file.prefix).suffix.lower()
        if ext == ".apkg" or ext not in {".docx", ".pdf", ".txt"}:
            raise HTTPException(status_code=422, detail="unprocessable body")

        resp = await s3.get_object(Bucket=BUCKET_NAME, Key=file.prefix)
        file_bytes = await resp["Body"].read()

        get_text: tp.Callable[[bytes], str] = {
            ".txt": bytes.decode,
            ".pdf": get_pdf_text,
            ".docx": get_docx_text,
        }[ext]
        return get_text(file_bytes)

    *_, video_id = request.video.strip().split(YOUTUBE_VIDEO_PREFIX)
    script_prefix = f"{user_id}/scripts/{video_id}/transcript.json"

    existing_file = (
        await sql.execute(select(File).where(File.prefix == script_prefix))
    ).scalar_one_or_none()

    if existing_file is not None:
        try:
            resp = await s3.get_object(Bucket=BUCKET_NAME, Key=script_prefix)
            text = (await resp["Body"].read()).decode("utf-8")
            request.file_id = existing_file.id
        except (BotoCoreError, ClientError, UnicodeDecodeError):
            pass
        else:
            return text

    video = yt.fetch(video_id)
    data = video.to_raw_data()
    text = "\n".join(d.get("text", "") for d in data).strip()

    script_file = File(
        id=uuid.uuid4(),
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


async def generate_partial(gen: GenApi, prompt: str, chunk: str) -> GeneratedFlashcard:
    json_schema = GeneratedFlashcard.model_json_schema()

    last_error: Exception | None = None
    for attempt in range(3):
        correction = ""
        if last_error is not None:
            correction = (
                "\n\nPrevious output failed validation. "
                f"Fix and regenerate valid JSON only. Error: {last_error}"
            )

        payload = {
            "text": prompt + chunk + correction,
            "sampling_params": {
                "temperature": 0.7,
                "max_new_tokens": 4000,
                "json_schema": json.dumps(json_schema),
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

        raw_text = result.get("text")
        try:
            generated_content = json.loads(raw_text, strict=False)
            flashcard = GeneratedFlashcard.model_validate(generated_content)
        except (TypeError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            logger.warning(
                "Generation payload invalid on attempt %d/3: %s",
                attempt + 1,
                exc,
            )
            continue

        return flashcard

    raise HTTPException(
        status_code=500,
        detail=(
            f"Invalid flashcard payload from generation API after 3 attempts: "
            f"{last_error}"
        ),
    )


@router.post("/", response_model=FileDataResponse, status_code=status.HTTP_201_CREATED)
async def generate_anki(
    request: YouTubeBody | FileBody,
    text: GenText,
    user_id: CurrentUserId,
    sql: SqlSession,
    s3: Storage,
    gen: GenApi,
) -> File:
    chunks = tuple(text[i : i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE))

    if not chunks:
        raise HTTPException(status_code=400, detail="No content to generate")

    flashcards = await asyncio.gather(
        *(generate_partial(gen, MIXED_PROMPT, chunk) for chunk in chunks)
    )

    file_id = uuid.uuid4()
    card_type = "mixed_flashcards"
    filename = f"{card_type}_{file_id}.apkg"
    prefix = f"{user_id}/generated/{file_id}/{filename}"
    deck_name = f"LiveTrivia::{card_type}::{file_id}"

    with tf.TemporaryDirectory() as tmp_dir:
        package_path = Path(tmp_dir) / filename
        build_anki_package(flashcards, deck_name, package_path)
        package_bytes = package_path.read_bytes()

    await s3.put_object(
        Bucket=BUCKET_NAME,
        Key=prefix,
        Body=package_bytes,
        ContentType="application/zip",
    )

    if request.file_id is None:
        *_, video_id = request.video.strip().split(YOUTUBE_VIDEO_PREFIX)
        script_prefix = f"{user_id}/scripts/{video_id}/transcript.json"
        if (
            script := (
                await sql.execute(select(File).where(File.prefix == script_prefix))
            ).scalar_one_or_none()
        ) is None:
            raise HTTPException(404)
        request.file_id = script.id

    new_file = File(
        id=file_id,
        prefix=prefix,
        user_id=user_id,
        generated_from_id=request.file_id,
    )
    sql.add(new_file)
    await sql.commit()
    await sql.refresh(new_file)
    return new_file

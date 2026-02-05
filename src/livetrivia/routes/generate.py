import aiohttp
import io
import json
import zipfile as zf
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import select
from livetrivia.models.anki_deck import AnkiModel
from livetrivia.models.files import FileDataResponse
from livetrivia.routes.session import get_current_user
from livetrivia.db import (
    get_sql_session,
    get_s3_client,
    BUCKET_NAME,
    new_inmemory_anki_orm,
)
import uuid
from livetrivia.text_extraction import (
    YOUTUBE_VIDEO_PREFIX,
    get_yt_api,
    get_docx_text,
    get_pdf_text,
)
from livetrivia.utils import getenvs
from livetrivia.models.files import File

import typing_extensions as tp

if tp.TYPE_CHECKING:
    import youtube_transcript_api as yt
    import types_aiobotocore_s3 as aiob3t
    import sqlalchemy.ext.asyncio as sqlas
    from pydantic import ConfigDict
    import sqlalchemy as sqla


SGLANG_URL: str = getenvs()

router: APIRouter = APIRouter(prefix="/generate", tags=["generate"])


PROMPT = """You are an expert flashcard creator. Generate high-quality Anki flashcards from the provided text content.

## Instructions
1. Extract key concepts, facts, definitions, and relationships from the text
2. Create clear, concise question-answer pairs that test understanding
3. Each card should focus on ONE concept or fact
4. Questions should be specific and unambiguous
5. Answers should be brief but complete
6. Avoid trivial or overly obvious questions
7. Create 10-25 cards depending on content density

## Output Structure
Generate a valid AnkiModel JSON with:
- `col`: Collection metadata with a Basic note type model
- `notes`: Array of notes where `flds` contains "Front\\x1fBack" (question and answer separated by \\x1f)
- `cards`: Array of cards referencing the notes

## Col Configuration
- Use model ID 1 for Basic cards
- Use deck ID 1 for the default deck
- Set `mid` in notes to match the model ID
- Set `did` in cards to match the deck ID
- Use current epoch milliseconds for timestamps and IDs (ensure uniqueness)
- `guid` should be a unique 10-character alphanumeric string per note
- `csum` should be a simple hash (use first 8 digits of note ID)
- `sfld` should match the front field content

## Example Note Format
For a question "What is the capital of France?" with answer "Paris":
- `flds`: "What is the capital of France?\\x1fParis"
- `sfld`: "What is the capital of France?"

## Text Content to Process:
"""


CLOZE_PROMPT = """You are an expert flashcard creator. Generate high-quality Anki cloze deletion flashcards from the provided text content.

## Instructions
1. Extract key concepts, facts, definitions, and relationships from the text
2. Create cloze deletions that hide important terms, definitions, or concepts
3. Use {{c1::hidden text}} syntax for cloze deletions
4. Each note can have multiple cloze deletions (c1, c2, c3...) to create multiple cards
5. Provide enough context around the cloze for meaningful recall
6. Avoid hiding trivial words or creating ambiguous blanks
7. Create 10-25 notes depending on content density

## Output Structure
Generate a valid AnkiModel JSON with:
- `col`: Collection metadata with a Cloze note type model
- `notes`: Array of notes where `flds` contains the cloze text (with optional extra field separated by \\x1f)
- `cards`: Array of cards referencing the notes (one card per cloze number)

## Col Configuration
- Use model ID 2 for Cloze cards
- Use deck ID 1 for the default deck
- Set `mid` in notes to match the model ID
- Set `did` in cards to match the deck ID
- Use current epoch milliseconds for timestamps and IDs (ensure uniqueness)
- `guid` should be a unique 10-character alphanumeric string per note
- `csum` should be a simple hash (use first 8 digits of note ID)
- `sfld` should be the text with cloze markers stripped
- For notes with c1, c2, etc., create corresponding cards with `ord` 0, 1, etc.

## Example Cloze Formats
Single cloze: "The capital of France is {{c1::Paris}}"
Multiple clozes: "{{c1::Python}} is a {{c2::programming language}} created by {{c3::Guido van Rossum}}"

## Example Note Format
For "The mitochondria is the {{c1::powerhouse}} of the {{c2::cell}}":
- `flds`: "The mitochondria is the {{c1::powerhouse}} of the {{c2::cell}}\\x1f"
- `sfld`: "The mitochondria is the powerhouse of the cell"
- Create 2 cards: one with ord=0 (for c1), one with ord=1 (for c2)

## Text Content to Process:
"""


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
    user_id: uuid.UUID = Depends(get_current_user),
    yt: "yt.YouTubeTranscriptApi" = Depends(get_yt_api),
    s3: "aiob3t.S3Client" = Depends(get_s3_client),
    sql: "sqlas.AsyncSession" = Depends(get_sql_session),
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


@router.post("/", response_model=FileDataResponse, status_code=status.HTTP_201_CREATED)
async def generate_anki(
    input: YouTubeBody | FileBody,
    text: str = Depends(get_gen_text),
    user_id: uuid.UUID = Depends(get_current_user),
    sql: "sqlas.AsyncSession" = Depends(get_sql_session),
    anki: "sqlas.AsyncSession" = Depends(new_inmemory_anki_orm),
    s3: "aiob3t.S3Client" = Depends(get_s3_client),
    gen: aiohttp.ClientSession = Depends(get_gen_api),
) -> File:

    # Select the appropriate prompt based on cloze parameter
    prompt = CLOZE_PROMPT if input.cloze else PROMPT

    full_prompt = prompt + text

    payload = {
        "text": full_prompt,
        "sampling_params": {
            "temperature": 0.7,
            "max_new_tokens": 26000,
            "json_schema": json.dumps(AnkiModel.model_json_schema()),
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
    validated_model: AnkiModel = AnkiModel.model_validate(generated_content)

    file_id = uuid.uuid4()
    card_type = "cloze" if input.cloze else "basic"
    filename = f"{card_type}_{file_id}.apkg"
    prefix = f"{user_id}/generated/{file_id}/{filename}"

    await validated_model.add_to_sql(anki)

    buffer = io.BytesIO()

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

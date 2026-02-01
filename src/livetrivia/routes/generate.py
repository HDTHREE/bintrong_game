from fastapi import APIRouter, Depends, HTTPException, status
from livetrivia.models.files import File, FileDataResponse
from livetrivia.routes.session import get_current_user
from livetrivia.db import get_sql_session, get_s3_client, BUCKET_NAME
import uuid
import sqlalchemy.ext.asyncio as sqlas
import types_aiobotocore_s3 as aiob3t
import aiohttp
from livetrivia.utils import getenvs

import openai as ai

SGLANG_URL: str = getenvs()

router: APIRouter = APIRouter(prefix="/generate", tags=["generate"])



async def get_ai_client(base_url: str = Depends(lambda: SGLANG_URL)):
    yield ai.AsyncClient(base_url=base_url, api_key="dummy")


@router.post(
    "/{file_id}", response_model=FileDataResponse, status_code=status.HTTP_201_CREATED
)
async def generate_anki_from_file(
    file_id: uuid.UUID,
    cloze: bool = False,
    user_id: uuid.UUID = Depends(get_current_user),
    sql: sqlas.AsyncSession = Depends(get_sql_session),
    s3: aiob3t.S3Client = Depends(get_s3_client),
    ai: ai.AsyncClient = Depends(get_ai_client)
):
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
    file_content = await body.read()
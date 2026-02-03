import aiohttp
import json
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select
from livetrivia.models.files import FileDataResponse
from livetrivia.routes.session import get_current_user
from livetrivia.db import get_sql_session, get_s3_client, BUCKET_NAME
import uuid
from livetrivia.text_extraction import YOUTUBE_VIDEO_PREFIX, get_yt_api, get_docx_text, get_pdf_text
from livetrivia.utils import getenvs
from livetrivia.models.files import File

import typing_extensions as tp

if tp.TYPE_CHECKING:
    import youtube_transcript_api as yt
    import types_aiobotocore_s3 as aiob3t
    import sqlalchemy.ext.asyncio as sqlas

SGLANG_URL: str = getenvs()

router: APIRouter = APIRouter(prefix="/generate", tags=["generate"])



PROMPT = """
You are a world-class Anki flashcard creator that helps students create flashcards that help them remember facts, concepts, and ideas from videos. You will be given a video or document or snippet.
1. Identify key high-level concepts and ideas presented, including relevant equations. If the video is math or physics-heavy, focus on concepts. If the video isn't heavy on concepts, focus on facts.
2. Then use your own knowledge of the concept, ideas, or facts to flesh out any additional details (eg, relevant facts, dates, and equations) to ensure the flashcards are self-contained.
3. Make question-answer cards based on the video.
4. Keep the questions and answers roughly in the same order as they appear in the video itself.
5. If a video is provided, include timestamps in the question field in [ ] brackets at the end of the questions to the segment of the video that's relevant.

Output Format,
- Do not have the first row being "Question" and "Answer".
- The file will be imported into Anki. You should include each flashcard on a new line and use the pipe separator | to separate the question and answer. You should return a .txt file for me to download.
- When writing math, wrap any math with the \( ... \) tags [eg, \( a^2+b^2=c^2 \) ] . By default this is inline math. For block math, use \[ ... \]. Decide when formatting each card.
- When writing chemistry equations, use the format \( \ce{C6H12O6 + 6O2 -&gt; 6H2O + 6CO2} \) where the \ce is required for MathJax chemistry.
- Put everything in a code block.
- Do not use a new line for visual purposes in the answer or question as this is the indicator for a new flashcard. If you need to list smth, do it with <br>.
- For bold text, use <b> </b>. For italic text, use <i> </i>.

Be sure to be exhaustive. Cover as much as you can, do not stop when your output is getting too long. You can handle up to 200 cards, so please allow yourself to be as exhaustive as possible.

MESSAGE TO PROCESS:

"""

CLOZE_PROMPT = """
You are a world-class Anki **cloze-deletion** flashcard creator. I will give you a video, document, or snippet.
1. Skim the material and identify the key concepts, facts, dates, definitions, and equations that a learner should recall long-term.
• If the material is math/physics-heavy, prioritize conceptual understanding and derivations.
• If it is fact-heavy, prioritize precise details and chronology.
2. Expand briefly on each point with any extra context (examples, typical pitfalls, historical notes) so that every card is *self-contained*. A learner should not need the original source to answer.
3. Convert each point into one (or at most two) **well-formed cloze deletions**:
• Embed the hidden info inside `{{c1:: … }}`; use `c2`, `c3`, … if a second deletion is *really* necessary.
• Keep **one atomic fact per cloze**. If you must hide multiple parts of an equation, consider separate cards.
• If helpful, add a short *Hint* in the curly braces after `::` (e.g. `{{c1::Planck's constant::symbol h}}`).
• When including math, wrap it with LaTeX: inline `$begin:math:text$ … $end:math:text$` or block `$begin:math:display$ … $end:math:display$` as appropriate.
• For chemistry, use MathJax chem: `$begin:math:text$ \\ce{C6H12O6 + 6O2 -> 6H2O + 6CO2} $end:math:text$`.
4. Maintain the **original order** of appearance from the source.
5. If a video is provided, append the relevant timestamp(s) in square brackets **at the end** of the cloze line: `[12:34]` or `[12:34–13:02]`.

**Output format**
- Do not have the first row being "Cloze Text" and "Back Extra".
- The file will be imported into Anki. You should include each flashcard on a new line and use the pipe separator | to separate the cloze text and extra information on the back. You should return a .txt file for me to download.
- When writing math, wrap any math with the \( ... \) tags [eg, \( a^2+b^2=c^2 \) ] . By default this is inline math. For block math, use \[ ... \]. Decide when formatting each card.
- When writing chemistry equations, use the format \( \ce{C6H12O6 + 6O2 -&gt; 6H2O + 6CO2} \) where the \ce is required for MathJax chemistry.
- Put everything in a code block.
- Do not use a new line for visual purposes in the answer or question as this is the indicator for a new flashcard. If you need to list smth, do it with <br>.

Be sure to be exhaustive. Cover as much as you can, do not stop when your output is getting too long. You can handle up to 200 cards, so please allow yourself to be as exhaustive as possible.

MESSAGE TO PROCESS:

"""



class YouTubeBody(BaseModel):
    video: str

    @property
    def file_id(self):
        return None


class FileBody(BaseModel):
    file_id: uuid.UUID

    @property
    def video(self):
        return None


async def get_gen_api(url: str = Depends(lambda: SGLANG_URL)):
    yield aiohttp.ClientSession(base_url=url)



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
        if ext == ".anki" or ext not in {".docx",".pdf",".txt"}:
            raise HTTPException(status_code=422, detail="unprocessable body")
        # Get the bytes of the file
        resp = await s3.get_object(Bucket=BUCKET_NAME, Key=file.prefix)
        file_bytes = await resp.get("Body").read()

        # Parse the file based on extension.
        get_text: tp.Callable[[bytes], str] = {".txt": bytes.decode, ".pdf": get_pdf_text, ".docx": get_docx_text}.get(ext)
        return get_text(file_bytes)

    # Get youtube script text.
    *_, id = input.video.strip().split(YOUTUBE_VIDEO_PREFIX)
    data = yt.fetch(id).to_raw_data()
    return json.dumps(data)


@router.post("/", response_model=FileDataResponse, status_code=status.HTTP_201_CREATED)
async def generate_anki(
    cloze: bool = False,
    text: str = Depends(get_gen_text),
    user_id: uuid.UUID = Depends(get_current_user),
    sql: "sqlas.AsyncSession" = Depends(get_sql_session),
    gen: aiohttp.ClientSession = Depends(get_gen_api)
):

    raise RuntimeError()



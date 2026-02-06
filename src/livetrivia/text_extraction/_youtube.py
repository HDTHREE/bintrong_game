import typing_extensions as tp
import youtube_transcript_api as yt
from fastapi import Depends


api: yt.YouTubeTranscriptApi = yt.YouTubeTranscriptApi()


async def get_yt_api():
    yield api


YTApi: tp.TypeAlias = tp.Annotated[yt.YouTubeTranscriptApi, Depends(get_yt_api)]


YOUTUBE_VIDEO_PREFIX: str = "https://www.youtube.com/watch?v="


def _get_youtube_transcript(url: str) -> str:
    *_, id = url.strip().split(YOUTUBE_VIDEO_PREFIX)
    data: list[dict[str, str | float]] = api.fetch(id).to_raw_data()
    return " ".join(map(lambda d: d["text"], data)).strip()

import youtube_transcript_api as yt
import os
import threading
from livetrivia.utils import retry_with_backoff


api: yt.YouTubeTranscriptApi = yt.YouTubeTranscriptApi()


@retry_with_backoff(
    exceptions_to_catch=yt.YouTubeTranscriptApiException,
    logger=getattr(threading.local(), "LOGGER", None),
)
def _get_youtube_transcript(url: str) -> str:
    *_, id = url.strip().split("https://www.youtube.com/watch?v=")
    data: list[dict[str, str | float]] = api.fetch(id).to_raw_data()
    return " ".join(map(lambda d: d["text"], data)).strip()


if __name__ == "__main__":
    print(_get_youtube_transcript("https://www.youtube.com/watch?v=IFO7qTQKIXQ"))
    print(_get_youtube_transcript("IFO7qTQKIXQ"))

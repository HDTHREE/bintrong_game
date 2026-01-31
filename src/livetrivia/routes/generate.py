from fastapi import Depends
from livetrivia.utils import getenvs
import aiohttp


SGLANG_URL: str = getenvs()


async def get_sgl_session(url: str = Depends(lambda: SGLANG_URL)):
    yield aiohttp.ClientSession(base_url=url)
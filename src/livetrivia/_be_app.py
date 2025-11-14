#!/usr/bin/env python3
try:
    from dotenv import load_dotenv

    _: bool = load_dotenv(r".dev.env")
finally:
    ...

import os
import typing_extensions as tp
from fastapi import FastAPI


SGLANG_URL: str | tp.Never = os.environ.get("SGLANG_URL", None) or exit()


api: FastAPI = FastAPI()


__all__: tuple[str] = ("api",)


@api.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(api)

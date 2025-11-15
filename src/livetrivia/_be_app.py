#!/usr/bin/env python3
try:
    from dotenv import load_dotenv

    _: bool = load_dotenv(r".dev.env")
finally:
    ...

import os
import typing_extensions as tp
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import SQLModel, create_engine
from sqlalchemy.engine import Engine



SGLANG_URL, SQLITE_URL = map(lambda prop: os.getenv(prop) or exit(code=1), ("SGLANG_URL", "SQLITE_URL", ))


@asynccontextmanager
async def lifespan(_: FastAPI) -> tp.AsyncGenerator[None, None, None]:
    global SQLITE_URL
    engine: Engine = create_engine(SQLITE_URL)
    SQLModel.metadata.create_all(engine)
    yield


api: FastAPI = FastAPI(lifespan=lifespan)


__all__: tuple[str] = ("api",)


@api.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(api)

#!/usr/bin/env python3
try:
    from dotenv import load_dotenv

    _: bool = load_dotenv(r".dev.env")
finally:
    ...

import typing_extensions as tp
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import SQLModel
from livetrivia.db import get_async_engine
from livetrivia.utils import getenvs


SQLITE_URL: str = getenvs()


@asynccontextmanager
async def lifespan(_: FastAPI) -> tp.AsyncGenerator[None, None]:
    get_async_engine_context = asynccontextmanager(get_async_engine)
    async with (get_async_engine_context(SQLITE_URL) as engine, engine.begin() as conn):
        await conn.run_sync(SQLModel.metadata.create_all)
        yield


api: FastAPI = FastAPI(lifespan=lifespan)


__all__: tuple[str] = ("api",)


@api.get("/")
async def root():
    return {"message": "Hello World"}


try:
    from livetrivia.routes.user import router as _user_router

    api.include_router(_user_router, prefix="/api")
except Exception as e:
    print(e)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(api)

#!/usr/bin/env python3
try:
    from dotenv import load_dotenv

    _: bool = load_dotenv(r".dev.env")
finally:
    ...

import typing_extensions as tp
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import SQLModel, create_engine
from livetrivia.utils import getenvs


@asynccontextmanager
async def lifespan(_: FastAPI) -> tp.AsyncGenerator[None, None]:
    SQLModel.metadata.create_all(engine)
    yield


api: FastAPI = FastAPI(lifespan=lifespan)


__all__: tuple[str] = ("api",)


@api.get("/")
async def root():
    return {"message": "Hello World"}


try:
    from livetrivia.routes.auth_and_files import router as routes_router

    api.include_router(routes_router, prefix="/api")
except Exception as e:
    # print(e)
    ...


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(api)

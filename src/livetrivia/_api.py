#!/usr/bin/env python3
try:
    from dotenv import load_dotenv

    _: bool = load_dotenv(r".dev.env")
finally:
    ...

from fastapi.responses import RedirectResponse
from fastapi import FastAPI
from livetrivia.db import lifespan


api: FastAPI = FastAPI(lifespan=lifespan)


__all__: tuple[str] = ("api",)


@api.get("/", response_class=RedirectResponse, tags=["docs"])
async def root() -> RedirectResponse:
    return RedirectResponse("/docs")


try:
    from livetrivia.routes.user import router as _user_router
    from livetrivia.routes.session import router as _session_router
    from livetrivia.routes.files import router as _files_router
    from livetrivia.routes.game import router as _game_router
    from livetrivia.routes.round import router as _round_router
    from livetrivia.routes.generate import router as _generate_router

    api.include_router(_user_router, prefix="/api")
    api.include_router(_session_router, prefix="/api")
    api.include_router(_files_router, prefix="/api")
    api.include_router(_game_router, prefix="/api")
    api.include_router(_round_router, prefix="/api")
    api.include_router(_generate_router, prefix="/api")
except Exception as e:
    print(e)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(api)

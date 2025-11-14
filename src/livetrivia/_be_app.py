try:
    from dotenv import load_dotenv

    _: bool = load_dotenv(r".dev.env")
finally:
    ...

import os
import typing_extensions as tp
from fastapi import FastAPI


SGLANG_URL: str | tp.Never = os.environ.get("SGLANG_URL", None) or exit()


app: FastAPI = FastAPI()



__all__: tuple[str] = ("app",)


@app.get("/")
async def root():
    return {"message": "Hello World"}

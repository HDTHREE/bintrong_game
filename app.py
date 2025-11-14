try:
    from dotenv import load_dotenv

    _: bool = load_dotenv(r".dev.env")
finally:
    ...

import os
from fastapi import FastAPI


SGLANG_URL: str = os.environ.get("SGLANG_URL") or exit()


app: FastAPI = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}

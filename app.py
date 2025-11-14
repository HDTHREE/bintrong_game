import os
from fastapi import FastAPI
from dotenv import load_dotenv


_: bool = load_dotenv(r".dev.env")


SGLANG_URL: str = os.environ.get("SGLANG_URL") or exit()


app: FastAPI = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


#!/usr/bin/env python3
from fastapi import APIRouter, Depends, HTTPException, UploadFile, Header
from sqlmodel import select, Session
from pydantic import BaseModel
import uuid
from pathlib import Path
import shutil

from livetrivia.models.user import User, File as FileModel
from livetrivia.db import get_session


router = APIRouter()


class SignupRequest(BaseModel):
    email: str


@router.post("/signup")
def signup(req: SignupRequest, session: Session = Depends(get_session)):
    stmt = select(User).where(User.email == req.email)
    user = session.exec(stmt).first()
    if user:
        return {"token": str(user.id), "user": {"id": str(user.id), "email": user.email}}
    user = User(email=req.email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"token": str(user.id), "user": {"id": str(user.id), "email": user.email}}


@router.post("/login")
def login(req: SignupRequest, session: Session = Depends(get_session)):
    stmt = select(User).where(User.email == req.email)
    user = session.exec(stmt).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"token": str(user.id), "user": {"id": str(user.id), "email": user.email}}


def get_current_user(authorization: str | None = Header(None), session: Session = Depends(get_session)) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ", 1)[1].strip()
    try:
        uid = uuid.UUID(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    stmt = select(User).where(User.id == uid)
    user = session.exec(stmt).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/files/upload", status_code=201)
def upload_file(file: UploadFile, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    user_dir = STORAGE_DIR / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(file.filename).name
    dest = user_dir / filename
    i = 1
    base = dest.stem
    suf = dest.suffix
    while dest.exists():
        dest = user_dir / f"{base}_{i}{suf}"
        i += 1
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    file_rec = FileModel(prefix=str(dest.relative_to(Path.cwd())), user_id=current_user.id)
    session.add(file_rec)
    session.commit()
    session.refresh(file_rec)
    return {"id": str(file_rec.id), "prefix": file_rec.prefix}


@router.get("/files")
def list_files(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    stmt = select(FileModel).where(FileModel.user_id == current_user.id)
    files = session.exec(stmt).all()
    return [{"id": str(f.id), "prefix": f.prefix} for f in files]

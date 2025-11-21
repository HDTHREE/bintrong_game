#!/usr/bin/env python3
from sqlmodel import create_engine, Session
from livetrivia.utils import getenvs


SGLANG_URL, SQLITE_URL = getenvs()

# shared engine for the application
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})


def get_session():
    """Dependency that yields a SQLModel Session."""
    with Session(engine) as session:
        yield session

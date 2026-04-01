import os
import asyncio
from pathlib import Path

import pytest
import sqlalchemy.ext.asyncio as sqlas
import sqlalchemy.orm as sqlorm
from sqlmodel import SQLModel


os.environ.setdefault("SQL_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("S3_URL", "http://localhost:9000")
os.environ.setdefault("S3_REGION", "us-east-1")
os.environ.setdefault("BUCKET_NAME", "test-bucket")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("SGLANG_URL", "http://localhost:30000")


async def _create_schema(engine: sqlas.AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)


async def _drop_schema(engine: sqlas.AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture(scope="session")
def async_test_engine() -> sqlas.AsyncEngine:
    engine = sqlas.create_async_engine(os.environ["SQL_URL"])
    asyncio.run(_create_schema(engine))
    try:
        yield engine
    finally:
        asyncio.run(_drop_schema(engine))
        asyncio.run(engine.dispose())


@pytest.fixture
def async_test_session_factory(
    async_test_engine: sqlas.AsyncEngine,
) -> sqlorm.sessionmaker:
    return sqlorm.sessionmaker(
        bind=async_test_engine,
        class_=sqlas.AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture
def outputs_root() -> Path:
    root = Path(__file__).parent / "outputs"
    root.mkdir(exist_ok=True)
    return root

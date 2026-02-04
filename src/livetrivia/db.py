import asyncio
from contextlib import asynccontextmanager
import aioboto3
from sqlmodel import SQLModel
import typing_extensions as tp
import sqlalchemy.ext.asyncio as sqlas
import sqlalchemy.orm as sqlorm
from livetrivia.utils import getenvs
from fastapi import Depends

if tp.TYPE_CHECKING:
    from fastapi import Depends, FastAPI
    import types_aiobotocore_s3 as aiob3t


SQL_URL, S3_URL, S3_REGION, BUCKET_NAME = getenvs()


async def get_sql_engine(
    url: str = Depends(lambda: SQL_URL),
) -> tp.AsyncGenerator[sqlas.AsyncEngine]:
    yield _get_sql_engine(url=url)


async def new_memory_sql_engine() -> tp.AsyncGenerator[sqlas.AsyncEngine]:
    yield _get_sql_engine(url=":memory:")


async def _get_sql_engine(url: str) -> tp.AsyncGenerator[sqlas.AsyncEngine]:
    yield sqlas.create_async_engine(url)


async def get_sql_session(
    async_engine: sqlas.AsyncEngine = Depends(get_sql_engine),
) -> tp.AsyncGenerator[sqlas.AsyncSession]:
    async_session: sqlorm.Session = sqlorm.sessionmaker(
        bind=async_engine, class_=sqlas.AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


async def get_s3_session() -> tp.AsyncGenerator[aioboto3.Session]:
    yield aioboto3.Session()  # TODO prob add stuff here


async def get_s3_client(
    url: str = Depends(lambda: S3_URL),
    region_name=Depends(lambda: S3_REGION),
    aws_session: aioboto3.Session = Depends(get_s3_session),
) -> "tp.AsyncGenerator[aiob3t.S3Client]":
    async with aws_session.client(
        "s3",
        endpoint_url=url,
        region_name=region_name,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    ) as s3:
        yield s3


@asynccontextmanager
async def lifespan(_: "FastAPI") -> tp.AsyncGenerator[None, None]:
    get_s3_session_context = asynccontextmanager(get_s3_session)
    get_s3_client_context = asynccontextmanager(get_s3_client)

    async with (
        get_s3_session_context() as aws_session,
        get_s3_client_context(S3_URL, S3_REGION, aws_session) as s3,
    ):
        await s3.create_bucket(Bucket=BUCKET_NAME)

    get_sql_engine_context = asynccontextmanager(get_sql_engine)
    async with get_sql_engine_context(SQL_URL) as engine, engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        yield

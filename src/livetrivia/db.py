import contextlib as cl
import aioboto3
from sqlmodel import SQLModel
import typing_extensions as tp
import sqlalchemy.ext.asyncio as sqlas
import sqlalchemy.orm as sqlorm
from livetrivia.utils import getenvs
from livetrivia.models.anki_deck import create_anki_tables
from fastapi import Depends
import logging

if tp.TYPE_CHECKING:
    from fastapi import Depends, FastAPI
    import types_aiobotocore_s3 as aiob3t


logger: logging.Logger = logging.Logger(__name__)
"""Logger for db module to log failures to."""


SQL_URL, S3_URL, S3_REGION, BUCKET_NAME = getenvs(logger=logger)
"""Enivronment variables for database and S3 configuration."""


async def get_sql_engine(
    url: str = Depends(lambda: SQL_URL),
) -> tp.AsyncGenerator[sqlas.AsyncEngine]:
    """Dependency async generator that yields an async SQLAlchemy engine."""
    async for engine in _get_sql_engine(url=url):
        yield engine


async def new_inmemory_sql_engine() -> tp.AsyncGenerator[sqlas.AsyncEngine]:
    """Dependency async generator that yields an async SQLAlchemy engine (in-memory SQLite). Anki use case (i.e. tables are created)."""
    # Create an in-memory SQLite engine. Note that this database is re-created each time (i.e. it is ephemeral).
    # This table isn't even persisted between API calls. This depedency simply provides a fresh in-memory database each time it is called for `.db` file generation.
    async for engine in _get_sql_engine("sqlite+aiosqlite:///:memory:"):
        yield engine


async def _get_sql_engine(url: str) -> tp.AsyncGenerator[sqlas.AsyncEngine]:
    """Creates and yields an async SQLAlchemy engine. Common function for other engine dependencies."""
    yield sqlas.create_async_engine(url)


async def get_sql_session(
    async_engine: sqlas.AsyncEngine = Depends(get_sql_engine),
) -> tp.AsyncGenerator[sqlas.AsyncSession]:
    """SQLAlchemy Async Session dependency async generator. Provides an injected dependency for SQL operations."""
    async_session: sqlorm.Session = sqlorm.sessionmaker(
        bind=async_engine, class_=sqlas.AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


async def new_inmemory_anki_orm(
    async_engine: sqlas.AsyncEngine = Depends(new_inmemory_sql_engine),
) -> tp.AsyncGenerator[sqlas.AsyncSession]:
    """SQLAlchemy Async Session dependency async generator for Anki ORM. Since this database is re-created each time, tables are set each time as well."""
    # Create Anki tables.
    async with async_engine.begin() as connection:
        await connection.run_sync(create_anki_tables)
    # Create and yield the session.
    async_session = sqlorm.sessionmaker(
        bind=async_engine, class_=sqlas.AsyncSession, expire_on_commit=False
    )
    session: sqlas.AsyncSession
    async with async_session() as session:
        yield session


async def get_s3_session() -> tp.AsyncGenerator[aioboto3.Session]:
    """Aioboto3 Session dependency async generator."""
    yield aioboto3.Session()  # TODO prob add stuff here


async def get_s3_client(
    url: str = Depends(lambda: S3_URL),
    region_name=Depends(lambda: S3_REGION),
    aws_session: aioboto3.Session = Depends(get_s3_session),
) -> "tp.AsyncGenerator[aiob3t.S3Client]":
    """Aioboto3 S3 Client dependency async generator."""
    # Use dummy AWS credentials for localstack/testing.
    aws_access_key_id, aws_secret_access_key = ("test", "test")

    async with aws_session.client(
        "s3",
        endpoint_url=url,
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    ) as s3:
        yield s3


@cl.asynccontextmanager
async def lifespan(_: "FastAPI") -> tp.AsyncGenerator[None, None]:
    """FastAPI lifespan. Used to set up type ORM and creating the named bucket."""
    get_s3_session_context: cl.AbstractAsyncContextManager = cl.asynccontextmanager(
        get_s3_session
    )
    get_s3_client_context: cl.AbstractAsyncContextManager = cl.asynccontextmanager(
        get_s3_client
    )

    async with (
        get_s3_session_context() as aws_session,
        get_s3_client_context(S3_URL, S3_REGION, aws_session) as s3,
    ):
        await s3.create_bucket(Bucket=BUCKET_NAME)

    get_sql_engine_context: cl.AbstractAsyncContextManager = cl.asynccontextmanager(
        get_sql_engine
    )
    engine: sqlas.AsyncEngine
    connection: sqlas.AsyncConnection
    async with get_sql_engine_context(SQL_URL) as engine, engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
        yield


SqlSession: tp.TypeAlias = tp.Annotated[sqlas.AsyncSession, Depends(get_sql_session)]
"""SQLAlchemy Async Session dependency type alias. Provides an injected dependency for sql operations."""


S3Client: tp.TypeAlias = tp.Annotated["aiob3t.S3Client", Depends(get_s3_client)]
"""Aioboto3 S3 Client dependency type alias. Provides an injected dependency for S3 operations."""


AnkiOrmSession: tp.TypeAlias = tp.Annotated[
    sqlas.AsyncSession, Depends(new_inmemory_anki_orm)
]
"""SQLAlchemy Async Session dependency type alias. Functionally equivalent to `SqlSession` but in-memory SQLite database and uses Anki tables pre-created."""

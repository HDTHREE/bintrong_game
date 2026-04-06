import contextlib as cl
import os
import aioboto3
from sqlmodel import SQLModel
import typing_extensions as tp
import sqlalchemy.ext.asyncio as sqlas
import sqlalchemy.orm as sqlorm
from livetrivia.utils import getenvs
from livetrivia.storage import StorageClient
from livetrivia.game_server_manager import (
    GameServerManager,
    DockerGameServerManager,
)
from fastapi import Depends
import logging

if tp.TYPE_CHECKING:
    from fastapi import FastAPI
    import types_aiobotocore_s3 as aiob3t


logger: logging.Logger = logging.Logger(__name__)
"""Logger for db module to log failures to."""


SQL_URL, S3_URL, S3_REGION, BUCKET_NAME = getenvs(logger=logger)
"""Enivronment variables for database and S3 configuration."""

_USE_POSTGRES: bool = "postgresql" in SQL_URL
DEPLOYMENT_MODE: str = os.getenv("DEPLOYMENT_MODE", "docker")

if not _USE_POSTGRES and S3_URL is None:
    raise RuntimeError(
        "Cannot start livetrivia backend with current data storage configuration."
    )


async def get_sql_engine(
    url: str = Depends(lambda: SQL_URL),
) -> tp.AsyncGenerator[sqlas.AsyncEngine]:
    """Dependency async generator that yields an async SQLAlchemy engine."""
    async for engine in _get_sql_engine(url=url):
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


async def get_s3_session() -> tp.AsyncGenerator[aioboto3.Session]:
    """Aioboto3 Session dependency async generator."""
    yield aioboto3.Session()


async def get_s3_client(
    url: str = Depends(lambda: S3_URL),
    region_name=Depends(lambda: S3_REGION),
    aws_session: aioboto3.Session = Depends(get_s3_session),
) -> "tp.AsyncGenerator[aiob3t.S3Client]":
    """Aioboto3 S3 Client dependency async generator."""
    aws_access_key_id, aws_secret_access_key = ("test", "test")

    async with aws_session.client(
        "s3",
        endpoint_url=url,
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    ) as s3:
        yield s3


async def get_storage(
    async_engine: sqlas.AsyncEngine = Depends(get_sql_engine),
) -> tp.AsyncGenerator[StorageClient]:
    """Dependency that yields a :class:`~livetrivia.storage.StorageClient`.

    Yields a DB-backed instance when running against PostgreSQL, or an S3-backed
    instance (via LocalStack) when running in development.
    """
    if _USE_POSTGRES:
        yield StorageClient(sql_engine=async_engine)
        return

    aws_session = aioboto3.Session()
    aws_access_key_id, aws_secret_access_key = ("test", "test")
    async with aws_session.client(
        "s3",
        endpoint_url=S3_URL,
        region_name=S3_REGION,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    ) as s3:
        yield StorageClient(s3=s3)


@cl.asynccontextmanager
async def lifespan(_: "FastAPI") -> tp.AsyncGenerator[None, None]:
    """FastAPI lifespan. Used to set up type ORM and creating the named bucket."""
    if not _USE_POSTGRES:
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
    async with get_sql_engine_context(SQL_URL) as engine:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
    yield

    manager = _get_game_server_manager()
    await manager.stop_all_game_servers()


SqlSession: tp.TypeAlias = tp.Annotated[sqlas.AsyncSession, Depends(get_sql_session)]
"""SQLAlchemy Async Session dependency type alias. Provides an injected dependency for sql operations."""


S3Client: tp.TypeAlias = tp.Annotated["aiob3t.S3Client", Depends(get_s3_client)]
"""Aioboto3 S3 Client dependency type alias. Provides an injected dependency for S3 operations."""

Storage: tp.TypeAlias = tp.Annotated[StorageClient, Depends(get_storage)]
"""Unified storage dependency. Uses PostgreSQL in production, S3/LocalStack in development."""


def _get_game_server_manager() -> GameServerManager:
    if DEPLOYMENT_MODE == "kubernetes":
        from livetrivia.k8s_manager import K8sGameServerManager

        return K8sGameServerManager()
    return DockerGameServerManager()


async def get_game_server_manager() -> tp.AsyncGenerator[GameServerManager]:
    """Dependency that yields the active :class:`GameServerManager` backend."""
    yield _get_game_server_manager()


GameServerDep: tp.TypeAlias = tp.Annotated[
    GameServerManager, Depends(get_game_server_manager)
]
"""Game server manager dependency. Uses Docker or Kubernetes based on DEPLOYMENT_MODE."""

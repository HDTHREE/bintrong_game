"""Unified file storage abstraction.

In development (SQLite / LocalStack S3) the :class:`StorageClient` delegates to an
aioboto3 S3 client.  In production (PostgreSQL) it persists binary objects directly
into the :class:`~livetrivia.models.files.FileBlob` table, eliminating the need for
an external object-storage service.

The environment is inferred from the SQL connection URL: if it contains
``"postgresql"`` the class uses the DB backend; otherwise it uses S3.
"""

import typing_extensions as tp
import sqlalchemy.ext.asyncio as sqlas
import sqlalchemy.orm as sqlorm
from livetrivia.models.files import FileBlob

if tp.TYPE_CHECKING:
    import types_aiobotocore_s3 as aiob3t


class _GetObjectResponse(tp.TypedDict, total=False):
    """Minimal typed dict that mirrors the relevant fields of the boto3 GetObject response."""

    Body: "_BodyStream"
    ContentType: str
    ContentLength: int


class _BodyStream:
    """Async-iterable byte stream backed by an in-memory ``bytes`` buffer."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    async def read(self, size: int = -1) -> bytes:
        """Read `size` bytes from the buffer."""
        if size == -1:
            chunk = self._data[self._pos :]
            self._pos = len(self._data)
        else:
            chunk = self._data[self._pos : self._pos + size]
            self._pos += len(chunk)
        return chunk


class StorageClient:
    """Unified storage client.

    Wraps either an S3 client (development) or a synchronous SQLAlchemy async
    session (production) behind a single interface that exposes the S3-style
    ``put_object``, ``get_object``, and ``delete_object`` methods used
    throughout the application.

    Parameters
    ----------
    s3:
        A live ``aioboto3`` S3 client.  Pass ``None`` when using the DB backend.
    sql_engine:
        An async SQLAlchemy engine pointing at a PostgreSQL database.
        Pass ``None`` when using the S3 backend.
    """

    def __init__(
        self: tp.Self,
        *,
        s3: "aiob3t.S3Client | None" = None,
        sql_engine: sqlas.AsyncEngine | None = None,
    ) -> None:
        if s3 is None and sql_engine is None:
            raise ValueError(
                "StorageClient requires either an S3 client or a SQL engine."
            )
        self._s3 = s3
        self._engine = sql_engine

    async def put_object(
        self: tp.Self,
        *,
        Bucket: str,  # noqa: N803 – keeps S3 naming parity
        Key: str,  # noqa: N803
        Body: bytes,  # noqa: N803
        ContentType: str = "application/octet-stream",  # noqa: N803
    ) -> None:
        """Store *Body* at *Key*.  *Bucket* is ignored in the DB backend."""
        if self._s3 is not None:
            await self._s3.put_object(
                Bucket=Bucket, Key=Key, Body=Body, ContentType=ContentType
            )
            return

        async with self._make_session() as session:
            existing = await session.get(FileBlob, Key)
            if existing is not None:
                existing.data = Body
                existing.content_type = ContentType
                session.add(existing)
            else:
                session.add(FileBlob(prefix=Key, data=Body, content_type=ContentType))
            await session.commit()

    async def get_object(
        self: tp.Self,
        *,
        Bucket: str,  # noqa: N803
        Key: str,  # noqa: N803
    ) -> _GetObjectResponse:
        """Return a response dict compatible with the boto3 ``GetObject`` shape."""
        if self._s3 is not None:
            return await self._s3.get_object(Bucket=Bucket, Key=Key)  # type: ignore[return-value]

        async with self._make_session() as session:
            blob = await session.get(FileBlob, Key)

        if blob is None:
            # Mirror the botocore error so callers can handle it uniformly.
            from botocore.exceptions import ClientError

            raise ClientError(
                {
                    "Error": {
                        "Code": "NoSuchKey",
                        "Message": "The specified key does not exist.",
                    }
                },
                "GetObject",
            )

        return _GetObjectResponse(
            Body=_BodyStream(blob.data),
            ContentType=blob.content_type,
            ContentLength=len(blob.data),
        )

    async def delete_object(
        self: tp.Self,
        *,
        Bucket: str,  # noqa: N803
        Key: str,  # noqa: N803
    ) -> None:
        """Delete the object at *Key*."""
        if self._s3 is not None:
            await self._s3.delete_object(Bucket=Bucket, Key=Key)
            return

        async with self._make_session() as session:
            blob = await session.get(FileBlob, Key)
            if blob is not None:
                await session.delete(blob)
                await session.commit()

    def _make_session(self: tp.Self) -> sqlas.AsyncSession:
        assert self._engine is not None
        factory: sqlorm.Session = sqlorm.sessionmaker(
            bind=self._engine,
            class_=sqlas.AsyncSession,
            expire_on_commit=False,
        )
        return factory()

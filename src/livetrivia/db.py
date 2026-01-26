import typing_extensions as tp
from fastapi import Depends
import sqlalchemy.ext.asyncio as sqlas
import sqlalchemy.orm as sqlorm
from livetrivia.utils import getenvs


SQLITE_URL: str = getenvs()


async def get_async_engine(URL: str = Depends(lambda: SQLITE_URL)) -> tp.AsyncGenerator[sqlas.AsyncEngine]:
    yield sqlas.create_async_engine(URL)


async def get_async_session(async_engine: sqlas.AsyncEngine = Depends(get_async_engine)) -> tp.AsyncGenerator[sqlas.AsyncSession]:
    async_session: sqlorm.Session = sqlorm.sessionmaker(bind=async_engine, class_=sqlas.AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

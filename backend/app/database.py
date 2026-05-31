from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def get_db_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


def make_engine(url: str):
    return create_async_engine(url)


def make_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)

"""Database engine and session management."""

from openg2p_fastapi_common.context import dbengine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine

    context_engine = dbengine.get()
    if context_engine is not None:
        return context_engine
    if _engine is not None:
        return _engine

    from .config import Settings

    config = Settings.get_config()
    if config.db_datasource:
        _engine = create_async_engine(config.db_datasource, echo=config.db_logging)
        return _engine
    raise RuntimeError("Catalogue database is not configured")


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)

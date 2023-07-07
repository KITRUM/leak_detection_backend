from contextvars import ContextVar

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import settings

__all__ = ("get_session", "engine", "CTX_SESSION")


engine: AsyncEngine = create_async_engine(
    settings.database.url, future=True, pool_pre_ping=True, echo=False
)


def get_session(engine: AsyncEngine | None = engine) -> AsyncSession:
    Session: async_sessionmaker = async_sessionmaker(
        engine, expire_on_commit=False, autoflush=False
    )

    return Session()


CTX_SESSION: ContextVar[AsyncSession] = ContextVar(
    "session", default=get_session()
)

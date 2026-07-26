from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)


# PRAGMAs are per-connection in SQLite and aiosqlite pools connections.
# Without this hook only the one connection used at startup is configured —
# new pooled connections silently skip the settings, which leaves orphan
# `moves` rows after sessions/games are deleted (UNIQUE collisions on game
# id reuse) AND raises immediate "database is locked" errors under any
# concurrency because the default `busy_timeout` is 0.
@event.listens_for(engine.sync_engine, "connect")
def _configure_sqlite_connection(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        # Wait for a competing writer instead of failing the request outright.
        # With concurrent games/sessions writing to the one SQLite file, a
        # writer can briefly queue behind another's commit; 30 s absorbs that
        # instead of surfacing a user-visible "database is locked". Defense in
        # depth — `place_move` no longer holds the write lock across the
        # multi-second KataGo genmove (that reorder is the primary fix). 5 s was
        # too short and froze live games. Combined with WAL (`enable_wal()`).
        cursor.execute("PRAGMA busy_timeout=30000")
    finally:
        cursor.close()

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def enable_wal() -> None:
    async with engine.begin() as conn:
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
        await conn.exec_driver_sql("PRAGMA synchronous=NORMAL;")
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON;")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

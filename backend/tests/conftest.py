from __future__ import annotations

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.engine_pool import set_adapter


@pytest_asyncio.fixture
async def db_engine():
    # Use a file-based temp DB so all connections see the same schema
    import os as _os
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    # Keep foreign-key enforcement consistent with runtime so CASCADE works.
    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "connect")
    def _fk_on(dbapi_conn, _rec):  # type: ignore[no-untyped-def]
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON;")
        cur.close()

    async with engine.begin() as conn:
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON;")
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
    try:
        _os.unlink(db_path)
    except OSError:
        pass


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        yield s


@pytest_asyncio.fixture
async def client(db_engine, monkeypatch):
    """Build app with a fresh in-memory DB + mock KataGo."""
    # Override DB
    from app import db as db_module
    db_module.engine = db_engine  # type: ignore[assignment]
    db_module.AsyncSessionLocal = async_sessionmaker(  # type: ignore[assignment]
        db_engine, expire_on_commit=False, class_=AsyncSession
    )

    # Force mock KataGo
    os.environ["KATAGO_MOCK"] = "true"
    from app.core.katago.mock import MockKataGoAdapter
    mock = MockKataGoAdapter()
    set_adapter(mock)
    await mock.start()

    # Build app (defer import so settings pick up env)
    from app.main import create_app
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    # Cleanup any lingering state
    from app.engine_pool import _states
    _states.clear()

    # Reset rate limiter between tests
    from app.rate_limit import rate_limiter
    rate_limiter._buckets.clear()

    # Reset nickname registry so client-based tests don't collide across runs
    from app.session_registry import registry
    registry._by_key.clear()

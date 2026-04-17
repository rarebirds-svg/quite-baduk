from __future__ import annotations

import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.models import User, Game, Move, AnalysisCache  # register models with metadata
from app.engine_pool import set_adapter, drop_state


@pytest_asyncio.fixture
async def db_engine():
    # Use a file-based temp DB so all connections see the same schema
    import tempfile, os as _os
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = tmp.name
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
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
    db_module.AsyncSessionLocal = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)  # type: ignore[assignment]

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

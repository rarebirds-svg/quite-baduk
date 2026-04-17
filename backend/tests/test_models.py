"""Test that ORM models can be created and queried in-memory SQLite."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.models import AnalysisCache, Game, Move, User


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON;")
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_user(session: AsyncSession) -> None:
    user = User(email="test@example.com", password_hash="hashed", display_name="Tester")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    assert user.id is not None
    assert user.locale == "ko"
    assert user.theme == "light"


@pytest.mark.asyncio
async def test_create_game(session: AsyncSession) -> None:
    user = User(email="player@example.com", password_hash="hashed", display_name="Player")
    session.add(user)
    await session.commit()

    game = Game(user_id=user.id, ai_rank="5k", handicap=0, komi=6.5, user_color="black")
    session.add(game)
    await session.commit()
    await session.refresh(game)
    assert game.id is not None
    assert game.status == "active"
    assert game.move_count == 0


@pytest.mark.asyncio
async def test_create_move(session: AsyncSession) -> None:
    user = User(email="m@example.com", password_hash="hashed", display_name="M")
    session.add(user)
    await session.commit()

    game = Game(user_id=user.id, ai_rank="1d", handicap=0, komi=6.5, user_color="black")
    session.add(game)
    await session.commit()

    move = Move(game_id=game.id, move_number=1, color="B", coord="Q16", captures=0)
    session.add(move)
    await session.commit()
    await session.refresh(move)
    assert move.id is not None
    assert move.is_undone is False


@pytest.mark.asyncio
async def test_create_analysis_cache(session: AsyncSession) -> None:
    user = User(email="a@example.com", password_hash="hashed", display_name="A")
    session.add(user)
    await session.commit()

    game = Game(user_id=user.id, ai_rank="3k", handicap=4, komi=0.5, user_color="black")
    session.add(game)
    await session.commit()

    cache = AnalysisCache(game_id=game.id, move_number=10, payload='{"winrate":0.52}')
    session.add(cache)
    await session.commit()
    await session.refresh(cache)
    assert cache.id is not None

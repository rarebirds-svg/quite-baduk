"""Test that ORM models can be created and queried in-memory SQLite."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.models import AnalysisCache, Game, Move, Session


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
async def test_create_session_row(session: AsyncSession) -> None:
    s = Session(token="t1", nickname="alice", nickname_key="alice")  # noqa: S106 (test session token, not a password)
    session.add(s)
    await session.commit()
    await session.refresh(s)
    assert s.id is not None
    assert s.last_seen_at is not None


@pytest.mark.asyncio
async def test_create_game(session: AsyncSession) -> None:
    s = Session(token="t2", nickname="bob", nickname_key="bob")  # noqa: S106 (test session token, not a password)
    session.add(s)
    await session.commit()
    await session.refresh(s)

    game = Game(
        session_id=s.id, ai_rank="5k", handicap=0, komi=6.5, user_color="black", board_size=19
    )
    session.add(game)
    await session.commit()
    await session.refresh(game)
    assert game.id is not None
    assert game.status == "active"
    assert game.move_count == 0


@pytest.mark.asyncio
async def test_create_move(session: AsyncSession) -> None:
    s = Session(token="t3", nickname="carol", nickname_key="carol")  # noqa: S106 (test session token, not a password)
    session.add(s)
    await session.commit()
    await session.refresh(s)

    game = Game(
        session_id=s.id, ai_rank="1d", handicap=0, komi=6.5, user_color="black", board_size=19
    )
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
    s = Session(token="t4", nickname="dan", nickname_key="dan")  # noqa: S106 (test session token, not a password)
    session.add(s)
    await session.commit()
    await session.refresh(s)

    game = Game(
        session_id=s.id, ai_rank="3k", handicap=4, komi=0.5, user_color="black", board_size=19
    )
    session.add(game)
    await session.commit()

    cache = AnalysisCache(game_id=game.id, move_number=10, payload='{"winrate":0.52}')
    session.add(cache)
    await session.commit()
    await session.refresh(cache)
    assert cache.id is not None


@pytest.mark.asyncio
async def test_game_persists_board_size(session: AsyncSession) -> None:
    s = Session(token="t5", nickname="eve", nickname_key="eve")  # noqa: S106 (test session token, not a password)
    session.add(s)
    await session.commit()
    await session.refresh(s)

    game = Game(
        session_id=s.id,
        ai_rank="5k",
        handicap=0,
        komi=6.5,
        user_color="black",
        board_size=9,
    )
    session.add(game)
    await session.commit()

    res = await session.execute(select(Game).where(Game.id == game.id))
    loaded = res.scalar_one()
    assert loaded.board_size == 9


@pytest.mark.asyncio
async def test_game_survives_session_delete(session: AsyncSession) -> None:
    """Games must persist after their originating session is deleted so the
    admin console's audit trail isn't lost on logout/idle-purge.
    session_id is SET NULL via ON DELETE SET NULL; the user_nickname
    snapshot continues to identify the player."""
    s = Session(token="t6", nickname="frank", nickname_key="frank")  # noqa: S106 (test session token, not a password)
    session.add(s)
    await session.commit()
    await session.refresh(s)

    session.add(Game(
        session_id=s.id, user_nickname="frank", ai_rank="5k", handicap=0,
        komi=6.5, user_color="black", board_size=19,
    ))
    await session.commit()

    await session.delete(s)
    await session.commit()

    res = await session.execute(select(Game))
    games = res.scalars().all()
    assert len(games) == 1
    assert games[0].session_id is None
    assert games[0].user_nickname == "frank"

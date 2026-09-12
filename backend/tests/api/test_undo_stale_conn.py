# stale WS 연결의 undo·계가 신청이 낡은 game 행으로 커밋하지 않는지 검증하는 회귀 테스트 (#84).
"""undo_move / score_by_request 동시성 — stale 연결이 낡은 행으로 커밋하지 않는다.

회귀 방지(#84, #81의 잔존 레이스): WS 재접속 시 새 연결은 자체 DB 세션으로
game 행을 로드하므로, 이전 연결이 락 안에서 커밋한 move_count·status·
undo_count 변경을 보지 못한다(stale). 예전 undo_move는 락 안에서 행을 refresh
하지 않고 in-memory move_count에서 -= 1 해 커밋했으므로, stale 연결의 undo가
잘못된(경우에 따라 음수) move_count를 DB에 남겨 이후 착수의 UNIQUE(game_id,
move_number) 충돌을 재발시킬 수 있었다. score_by_request도 락 획득 후 status를
재확인하지 않아 이미 끝난 대국을 다시 종료 처리할 수 있었다.
"""
from __future__ import annotations

import secrets

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.services.game_service as gs
from app.core.katago.mock import MockKataGoAdapter
from app.engine_pool import set_adapter
from app.models import Session
from app.models.game import Game
from app.models.move import Move as MoveRow
from app.services.game_service import (
    UNDO_LIMIT,
    GameError,
    create_game,
    place_move,
    resign_game,
    score_by_request,
    undo_move,
)


async def _make_session(db: AsyncSession, nickname: str) -> Session:
    s = Session(
        token=secrets.token_urlsafe(8), nickname=nickname, nickname_key=nickname
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _load_as_other_conn(
    db_b: AsyncSession, game_id: int, session_id: int
) -> tuple[Game, Session]:
    """재접속한 두 번째 WS 연결을 흉내 — 별도 세션으로 같은 행을 로드한다."""
    game_b = (await db_b.execute(select(Game).where(Game.id == game_id))).scalar_one()
    sess_b = (
        await db_b.execute(select(Session).where(Session.id == session_id))
    ).scalar_one()
    return game_b, sess_b


async def _move_numbers(db: AsyncSession, game_id: int) -> list[int]:
    return list(
        (
            await db.execute(
                select(MoveRow.move_number)
                .where(MoveRow.game_id == game_id)
                .order_by(MoveRow.move_number)
            )
        ).scalars().all()
    )


@pytest.mark.asyncio
async def test_stale_undo_decrements_from_fresh_move_count(
    db_engine, db_session: AsyncSession
) -> None:
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, "undo-stale")
    game = await create_game(
        db_session, session=s, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )

    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as db_b:
        game_b, sess_b = await _load_as_other_conn(db_b, game.id, s.id)
        assert game_b.move_count == 0

        # 연결 A가 1~4수를 커밋한다.
        await place_move(db_session, game=game, session=s, coord="E5")
        await place_move(db_session, game=game, session=s, coord="C3")
        assert game.move_count == 4

        # 연결 B는 move_count=0인 stale 객체로 undo — 예전엔 -2가 DB에 남았다.
        await undo_move(db_b, game=game_b, session=sess_b, steps=2)
        assert game_b.move_count == 2

    await db_session.refresh(game)
    assert game.move_count == 2
    assert await _move_numbers(db_session, game.id) == [1, 2]

    # 이후 착수가 3·4수로 정상 이어져야 한다 (UNIQUE 충돌·번호 건너뜀 없음).
    async with factory() as db_c:
        game_c, sess_c = await _load_as_other_conn(db_c, game.id, s.id)
        await place_move(db_c, game=game_c, session=sess_c, coord="F4")
    assert await _move_numbers(db_session, game.id) == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_stale_undo_on_finished_game_raises(
    db_engine, db_session: AsyncSession
) -> None:
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, "undo-stale2")
    game = await create_game(
        db_session, session=s, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )
    await place_move(db_session, game=game, session=s, coord="E5")

    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as db_b:
        game_b, sess_b = await _load_as_other_conn(db_b, game.id, s.id)

        # 연결 A가 기권으로 대국을 끝낸다. 연결 B의 객체는 여전히 active로 보인다.
        await resign_game(db_session, game=game, session=s)
        assert game_b.status == "active"

        with pytest.raises(GameError) as exc:
            await undo_move(db_b, game=game_b, session=sess_b, steps=2)
        assert exc.value.code == "GAME_NOT_ACTIVE"

    # 끝난 대국의 기보는 그대로 남아야 한다.
    assert await _move_numbers(db_session, game.id) == [1, 2]


@pytest.mark.asyncio
async def test_stale_undo_respects_fresh_undo_count(
    db_engine, db_session: AsyncSession
) -> None:
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, "undo-stale3")
    game = await create_game(
        db_session, session=s, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )

    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as db_b:
        game_b, sess_b = await _load_as_other_conn(db_b, game.id, s.id)
        assert game_b.undo_count == 0

        # 연결 A가 한도까지 undo를 소진한다.
        for coord in ("E5", "C3", "G7", "C7"):
            await place_move(db_session, game=game, session=s, coord=coord)
        for _ in range(UNDO_LIMIT):
            await undo_move(db_session, game=game, session=s, steps=2)
        assert game.undo_count == UNDO_LIMIT

        # stale 연결(undo_count=0)의 undo도 한도에 걸려야 한다.
        with pytest.raises(GameError) as exc:
            await undo_move(db_b, game=game_b, session=sess_b, steps=2)
        assert exc.value.code == "UNDO_LIMIT_EXCEEDED"

    assert await _move_numbers(db_session, game.id) == [1, 2]


@pytest.mark.asyncio
async def test_stale_score_request_on_finished_game_raises(
    db_engine, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    set_adapter(MockKataGoAdapter())
    # mock ownership은 전부 0.0이라 종반 게이트를 통과하지 못한다 — 게이트를 우회한다.
    monkeypatch.setattr(gs, "_endgame_phase_from_ownership", lambda *a, **kw: True)
    s = await _make_session(db_session, "score-stale")
    game = await create_game(
        db_session, session=s, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )

    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as db_b:
        game_b, sess_b = await _load_as_other_conn(db_b, game.id, s.id)

        await resign_game(db_session, game=game, session=s)
        assert game_b.status == "active"

        with pytest.raises(GameError) as exc:
            await score_by_request(db_b, game=game_b, session=sess_b)
        assert exc.value.code == "GAME_NOT_ACTIVE"

    # 기권 결과가 계가 결과로 덮어써지지 않아야 한다.
    await db_session.refresh(game)
    assert game.status == "resigned"
    assert game.result == "W+R"

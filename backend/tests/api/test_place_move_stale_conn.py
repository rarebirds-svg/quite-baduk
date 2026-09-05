# stale WS 연결의 착수가 moves UNIQUE 제약을 깨지 않는지 검증하는 회귀 테스트 (#81).
"""place_move 동시성 — stale 연결의 착수가 UNIQUE(game_id, move_number)를 깨지 않는다.

회귀 방지(#81): WS 재접속 시 새 연결은 자체 DB 세션으로 game 행을 로드하는데,
이전 연결의 place_move가 커밋한 move_count 증가를 반영하지 못한다(stale).
예전엔 그 stale 값으로 move_number를 계산해 같은 번호로 INSERT를 시도했고,
UNIQUE 제약 위반(IntegrityError)이 미처리 5xx로 터졌다 — game 378 move 89.
지금은 게임 락 안에서 game을 refresh해 최신 move_count·status 위에서
정상 착수(또는 GameError)로 처리돼야 한다.
"""
from __future__ import annotations

import secrets

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.katago.mock import MockKataGoAdapter
from app.engine_pool import set_adapter
from app.models import Session
from app.models.game import Game
from app.models.move import Move as MoveRow
from app.services.game_service import GameError, create_game, place_move, resign_game


async def _make_session(db: AsyncSession, nickname: str) -> Session:
    s = Session(
        token=secrets.token_urlsafe(8), nickname=nickname, nickname_key=nickname
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@pytest.mark.asyncio
async def test_stale_game_row_does_not_violate_unique(
    db_engine, db_session: AsyncSession
) -> None:
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, "stale")
    game = await create_game(
        db_session, session=s, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )

    # 재접속한 두 번째 WS 연결을 흉내 — 별도 세션으로 같은 행을 로드해 둔다.
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as db_b:
        game_b = (
            await db_b.execute(select(Game).where(Game.id == game.id))
        ).scalar_one()
        sess_b = (
            await db_b.execute(select(Session).where(Session.id == s.id))
        ).scalar_one()
        assert game_b.move_count == 0

        # 연결 A가 1수(user) + 2수(AI)를 커밋한다.
        await place_move(db_session, game=game, session=s, coord="E5")
        assert game.move_count == 2

        # 연결 B는 move_count=0인 stale 객체로 착수 — 예전엔 move_number=1로
        # 재INSERT를 시도해 IntegrityError가 났다. 이제 3·4수로 이어져야 한다.
        result = await place_move(db_b, game=game_b, session=sess_b, coord="C3")
        assert result.game_state is not None

    rows = (
        await db_session.execute(
            select(MoveRow.move_number)
            .where(MoveRow.game_id == game.id)
            .order_by(MoveRow.move_number)
        )
    ).scalars().all()
    assert rows == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_stale_game_row_on_finished_game_raises(
    db_engine, db_session: AsyncSession
) -> None:
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, "stale2")
    game = await create_game(
        db_session, session=s, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )

    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as db_b:
        game_b = (
            await db_b.execute(select(Game).where(Game.id == game.id))
        ).scalar_one()
        sess_b = (
            await db_b.execute(select(Session).where(Session.id == s.id))
        ).scalar_one()

        # 연결 A가 기권으로 대국을 끝낸다. 연결 B의 객체는 여전히 active로 보인다.
        await resign_game(db_session, game=game, session=s)
        assert game_b.status == "active"

        # stale 연결의 착수는 종료된 대국에 수를 추가하지 말고 거부돼야 한다.
        with pytest.raises(GameError) as exc:
            await place_move(db_b, game=game_b, session=sess_b, coord="C3")
        assert exc.value.code == "GAME_NOT_ACTIVE"

    rows = (
        await db_session.execute(
            select(MoveRow.move_number).where(MoveRow.game_id == game.id)
        )
    ).scalars().all()
    assert rows == []

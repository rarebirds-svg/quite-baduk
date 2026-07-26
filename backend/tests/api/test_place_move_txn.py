"""place_move 트랜잭션 경계 — DB 쓰기는 genmove *뒤* 한 배치로만 일어난다.

회귀 방지: 예전엔 사용자 수 INSERT~commit 사이에 KataGo genmove가 끼어
SQLite 쓰기 락이 수 초간 잡혔고, 동시 게임 쓰기가 'database is locked'로
실패해 대국이 얼었다. 이제 모든 DB 쓰기가 genmove 뒤 한 번에 커밋되므로,
genmove가 실패하면 아무것도 저장되지 않아야 한다(부분 저장·고착 없음).
"""
from __future__ import annotations

import secrets

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.katago.mock import MockKataGoAdapter
from app.engine_pool import set_adapter
from app.models import Session
from app.models.game import Game
from app.models.move import Move as MoveRow
from app.services.game_service import create_game, place_move


class _BoomGenmove(MockKataGoAdapter):
    """genmove만 실패시키는 어댑터 — analyze/play 등은 mock 그대로."""

    async def genmove(self, color: str) -> str:  # type: ignore[override]
        raise RuntimeError("katago genmove crashed")


async def _make_session(db: AsyncSession, nickname: str) -> Session:
    s = Session(
        token=secrets.token_urlsafe(8), nickname=nickname, nickname_key=nickname
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@pytest.mark.asyncio
async def test_genmove_failure_persists_nothing(db_session: AsyncSession) -> None:
    set_adapter(_BoomGenmove())
    s = await _make_session(db_session, "boom")
    game = await create_game(
        db_session, session=s, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )

    with pytest.raises(RuntimeError, match="genmove crashed"):
        await place_move(db_session, game=game, session=s, coord="E5")

    # place_move performs NO DB execute before genmove (the write batch is
    # after it), so genmove crashing leaves the session with no failed DB op
    # and no persisted move — only a discarded in-memory move_count bump.
    moves = (
        await db_session.execute(
            select(func.count(MoveRow.id)).where(MoveRow.game_id == game.id)
        )
    ).scalar_one()
    assert moves == 0, "genmove 실패 시 사용자 수도 저장되면 안 됨(락 홀드 회귀)"


@pytest.mark.asyncio
async def test_user_and_ai_move_both_persisted(db_session: AsyncSession) -> None:
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, "okmove")
    game = await create_game(
        db_session, session=s, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )

    await place_move(db_session, game=game, session=s, coord="E5")

    rows = (
        await db_session.execute(
            select(MoveRow.move_number, MoveRow.color)
            .where(MoveRow.game_id == game.id)
            .order_by(MoveRow.move_number)
        )
    ).all()
    assert [(r[0], r[1]) for r in rows] == [(1, "B"), (2, "W")]

    persisted = (
        await db_session.execute(select(Game).where(Game.id == game.id))
    ).scalar_one()
    assert persisted.move_count == 2

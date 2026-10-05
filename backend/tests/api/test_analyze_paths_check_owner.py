# analyze 계열 경로가 슬롯 소유권을 확인하고 불일치 시 재시드하는지 검증 (#109).
"""Every path that reads the shared slot board via ``adapter.analyze`` must do
what ``hint`` does: reseed when the game no longer owns the slot.

Otherwise a game whose ownership was dropped (another game interleaved, an
undo, a failed reseed) is analyzed on a board holding ghost stones, and the
winrate / dead-stone / score result is silently wrong (issue #109).
"""
from __future__ import annotations

import secrets

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.katago.mock import MockKataGoAdapter
from app.engine_pool import is_adapter_owner, set_adapter
from app.errors import GameError
from app.models import Session
from app.services.game_service import (
    _infer_dead_stones,
    create_game,
    estimate_score,
    score_by_request,
)


async def _make_session(db: AsyncSession, *, nickname: str) -> Session:
    s = Session(
        token=secrets.token_urlsafe(8),
        nickname=nickname,
        nickname_key=nickname,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _two_games_second_owns(db: AsyncSession, nickname: str):  # type: ignore[no-untyped-def]
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db, nickname=nickname)
    kw = dict(ai_rank="5k", handicap=0, user_color="black", board_size=9)
    first = await create_game(db, session=s, **kw)  # type: ignore[arg-type]
    second = await create_game(db, session=s, **kw)  # type: ignore[arg-type]
    assert is_adapter_owner(second.id)
    assert not is_adapter_owner(first.id)
    return s, first


@pytest.mark.asyncio
async def test_estimate_score_reseeds_when_not_owner(db_session: AsyncSession) -> None:
    s, first = await _two_games_second_owns(db_session, "own_est")
    await estimate_score(db_session, game=first, session=s)
    assert is_adapter_owner(first.id)


@pytest.mark.asyncio
async def test_score_by_request_reseeds_when_not_owner(db_session: AsyncSession) -> None:
    s, first = await _two_games_second_owns(db_session, "own_score")
    # 빈 판은 계가 단계가 아니라 거부되지만, 분석 전에 재시드는 끝나 있어야 한다.
    with pytest.raises(GameError):
        await score_by_request(db_session, game=first, session=s)
    assert is_adapter_owner(first.id)


@pytest.mark.asyncio
async def test_infer_dead_stones_reseeds_when_not_owner(db_session: AsyncSession) -> None:
    _, first = await _two_games_second_owns(db_session, "own_dead")
    from app.services.game_service import _replay_state

    state = await _replay_state(db_session, first)
    await _infer_dead_stones(first, state)
    assert is_adapter_owner(first.id)

# 같은 크기 대국 직후 치석 대국 생성 시 잔존 돌로 치석 배치가 거부되는 회귀(#97) 테스트.
from __future__ import annotations

import secrets

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.katago.mock import MockKataGoAdapter
from app.core.rules.sgf_coord import gtp_to_xy
from app.engine_pool import set_adapter
from app.models import Session
from app.services.game_service import create_game


class _StickyBoardAdapter(MockKataGoAdapter):
    """Mimics real KataGo GTP: `boardsize N` with N unchanged leaves the
    previous position on the board, and `play` on an occupied point errors
    instead of being silently ignored."""

    async def set_boardsize(self, size: int) -> None:
        if size == self.board_size:
            return
        await super().set_boardsize(size)

    async def play(self, color: str, coord: str) -> None:
        xy = gtp_to_xy(coord, self.board_size)
        if xy is not None and not self.board.is_empty(*xy):
            raise ValueError(f"KataGo rejected play {color} {coord}: illegal move")
        await super().play(color, coord)


async def _make_session(db: AsyncSession) -> Session:
    s = Session(token=secrets.token_urlsafe(8), nickname="h6", nickname_key="h6")
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@pytest.mark.asyncio
async def test_handicap_game_after_same_size_game_clears_stale_stones(
    db_session: AsyncSession,
) -> None:
    adapter = _StickyBoardAdapter()
    await adapter.start()
    # Previous 13x13 game on this slot left a White stone on D4 — the first
    # handicap point for 6 stones (game #479 → #480 in the incident).
    await adapter.set_boardsize(13)
    await adapter.play("W", "D4")
    set_adapter(adapter)

    s = await _make_session(db_session)
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=6,
        user_color="black",
        board_size=13,
    )

    assert game.handicap == 6
    # The stale White stone must be gone and D4 must now hold the handicap stone.
    d4 = gtp_to_xy("D4", 13)
    assert d4 is not None
    assert adapter.board.get(*d4) == "B"

# 어댑터 재시드 도중 예외가 나면 옛 소유자가 반쯤 복기된 보드에 남지 않는지 검증 (#108).
"""Reseed paths must drop slot ownership *before* the first board mutation.

``create_game``, ``_reseed_adapter`` and the analyze endpoint all start with
``clear_board`` and only record ownership at the very end. If anything raises
in between, the previous owner is still listed for a board that is now empty
or half replayed, so its next round takes the fast path on a wrong board
(issue #108). Ownership must be dropped up front and set only on success.
"""
from __future__ import annotations

import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.katago.mock import MockKataGoAdapter
from app.engine_pool import get_adapter, is_adapter_owner, set_adapter
from app.models import Session
from app.services.game_service import _reseed_adapter, create_game


class _FlakyAdapter(MockKataGoAdapter):
    """Fails ``set_komi`` on demand, i.e. after ``clear_board`` already ran."""

    def __init__(self) -> None:
        super().__init__()
        self.fail_komi = False

    async def set_komi(self, komi: float) -> None:
        if self.fail_komi:
            raise RuntimeError("katago died mid-reseed")
        await super().set_komi(komi)


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


@pytest.mark.asyncio
async def test_create_game_failure_drops_previous_owner(
    db_session: AsyncSession,
) -> None:
    adapter = _FlakyAdapter()
    set_adapter(adapter)
    s = await _make_session(db_session, nickname="reseed_create")
    first = await create_game(
        db_session, session=s, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )
    assert is_adapter_owner(first.id)

    adapter.fail_komi = True
    with pytest.raises(RuntimeError):
        await create_game(
            db_session, session=s, ai_rank="5k", handicap=0,
            user_color="black", board_size=9,
        )

    # The shared slot's board was wiped by the failed create; the first game
    # must not be trusted to still own it.
    assert not is_adapter_owner(first.id)


@pytest.mark.asyncio
async def test_reseed_adapter_failure_drops_previous_owner(
    db_session: AsyncSession,
) -> None:
    adapter = _FlakyAdapter()
    set_adapter(adapter)
    s = await _make_session(db_session, nickname="reseed_svc")
    game = await create_game(
        db_session, session=s, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )
    assert is_adapter_owner(game.id)

    adapter.fail_komi = True
    from app.core.rules.board import Board
    from app.core.rules.engine import GameState

    with pytest.raises(RuntimeError):
        await _reseed_adapter(game, GameState(board=Board(9), komi=game.komi))

    assert not is_adapter_owner(game.id)


@pytest.mark.asyncio
async def test_analyze_failure_drops_previous_owner(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "reseed_analyze"})
    assert r.status_code == 201
    body = {"ai_rank": "5k", "handicap": 0, "user_color": "black", "board_size": 9}
    first = (await client.post("/api/games", json=body)).json()
    second = (await client.post("/api/games", json=body)).json()
    first_id, second_id = int(first["id"]), int(second["id"])

    adapter = await get_adapter(first_id)
    assert is_adapter_owner(second_id)

    async def boom(_komi: float) -> None:
        raise RuntimeError("katago died mid-reseed")

    adapter.set_komi = boom  # type: ignore[method-assign]  # 테스트용 장애 주입
    try:
        await client.post(f"/api/games/{first_id}/analyze?moveNum=0")
    except RuntimeError:
        pass  # ASGI 테스트 클라이언트가 서버 예외를 그대로 전파하는 경우

    assert not is_adapter_owner(first_id)
    assert not is_adapter_owner(second_id)

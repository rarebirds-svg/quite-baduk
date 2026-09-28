# 라운드 실패로 유실된 착수가 어댑터에 남아 fast path를 어긋나게 하지 않는지 검증 (#105).
"""``place_move`` round failure must not leave a phantom stone in the adapter.

``_sync_adapter`` records the user's stone in the (shared) KataGo adapter
before the AI reply, the WS flush and the DB batch run. If any of those
raise — the client dropping mid-round is the common case (#39 path in
``ws.py``, swallowed quietly) — the stone stays in the adapter's replay
history but never reaches the rules state or the DB. The next round then
takes the fast path on top of a board KataGo thinks is one stone ahead,
and KataGo rejects the play (``illegal move``) — issue #105.
"""
from __future__ import annotations

import secrets

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.katago.mock import MockKataGoAdapter
from app.engine_pool import is_adapter_owner, set_adapter
from app.models import Session
from app.services.game_service import GameError, create_game, place_move


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
async def test_failed_round_drops_adapter_ownership_so_next_round_reseeds(
    db_session: AsyncSession,
) -> None:
    adapter = MockKataGoAdapter()
    set_adapter(adapter)
    s = await _make_session(db_session, nickname="desync")
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )
    assert is_adapter_owner(game.id)

    async def client_dropped(_state: object, _captures: int) -> None:
        # Starlette raises this when the WS closed between operations.
        raise RuntimeError('Cannot call "send" once a close message has been sent.')

    with pytest.raises(RuntimeError):
        await place_move(
            db_session, game=game, session=s, coord="E5", on_user_applied=client_dropped
        )

    # The stone reached the adapter but not the rules state / DB …
    assert adapter.move_history == [("B", "E5")]
    # … so the game must no longer be trusted as the slot owner.
    assert not is_adapter_owner(game.id)

    # The retry (user picks a different point after reconnecting) must
    # reseed: the adapter history equals the real history, no phantom E5.
    result = await place_move(db_session, game=game, session=s, coord="C3")
    expected = [(m.color, m.coord) for m in result.game_state.move_history]
    assert adapter.move_history == expected
    assert is_adapter_owner(game.id)


@pytest.mark.asyncio
async def test_user_illegal_move_keeps_adapter_ownership(
    db_session: AsyncSession,
) -> None:
    adapter = MockKataGoAdapter()
    set_adapter(adapter)
    s = await _make_session(db_session, nickname="keepown")
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )
    await place_move(db_session, game=game, session=s, coord="E5")
    assert is_adapter_owner(game.id)

    # Rejected by the rules engine before the adapter is touched: nothing
    # drifted, so the (expensive) reseed must not be forced on the next round.
    with pytest.raises(GameError):
        await place_move(db_session, game=game, session=s, coord="E5")
    assert is_adapter_owner(game.id)

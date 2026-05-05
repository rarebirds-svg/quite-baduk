"""Mid-game score estimate (OGS-style "Estimate Score" — peeks at KataGo's
ownership read without finalizing the game).

Distinct from /api/analyze (which gives top moves) and from score_request
(which finalizes). The estimate path returns winrate, score lead, AND the
full ownership map so the client can render a heatmap overlay.
"""
from __future__ import annotations

import secrets

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.katago.mock import MockKataGoAdapter
from app.engine_pool import set_adapter
from app.errors import GameError
from app.models import Session
from app.services.game_service import (
    ScoringDetail,
    create_game,
    estimate_score,
    place_move,
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


@pytest.mark.asyncio
async def test_estimate_score_returns_winrate_score_lead_and_ownership(
    db_session: AsyncSession,
) -> None:
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="es1")
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )

    estimate = await estimate_score(db_session, game=game, session=s)

    # Live data points the heatmap UI consumes.
    assert 0.0 <= estimate.winrate_black <= 1.0
    # ownership length matches board area; values in [-1, 1].
    assert len(estimate.ownership) == 9 * 9
    assert all(-1.0 <= v <= 1.0 for v in estimate.ownership)
    # score lead is a real number (negative or positive both legal).
    assert isinstance(estimate.score_lead_black, float)


@pytest.mark.asyncio
async def test_estimate_score_does_not_finalize_game(
    db_session: AsyncSession,
) -> None:
    """Distinct from score_request: estimate must leave the game playable."""
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="es2")
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )

    await estimate_score(db_session, game=game, session=s)

    # Refresh from DB — the row must still be active.
    await db_session.refresh(game)
    assert game.status == "active"
    assert game.result is None

    # And subsequent moves still work.
    result = await place_move(
        db_session, game=game, session=s, coord="E5"
    )
    assert result.game_state.board.size == 9


@pytest.mark.asyncio
async def test_estimate_score_rejects_non_owner(
    db_session: AsyncSession,
) -> None:
    set_adapter(MockKataGoAdapter())
    owner = await _make_session(db_session, nickname="owner")
    intruder = await _make_session(db_session, nickname="intruder")
    game = await create_game(
        db_session,
        session=owner,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )

    with pytest.raises(GameError) as ei:
        await estimate_score(db_session, game=game, session=intruder)
    assert ei.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_estimate_score_rejects_finished_game(
    db_session: AsyncSession,
) -> None:
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="es3")
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )
    game.status = "finished"
    game.result = "B+R"
    await db_session.commit()

    with pytest.raises(GameError) as ei:
        await estimate_score(db_session, game=game, session=s)
    assert ei.value.code == "GAME_NOT_ACTIVE"


@pytest.mark.asyncio
async def test_score_by_request_includes_ownership(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The score breakdown sheet renders an optional heatmap; the server
    must include the ownership read it already ran for dead-stone inference.

    Mock ownership is uniformly 0.0, which our endgame heuristic treats as
    "all empty cells contested" → not in endgame. Stub the gate so we can
    exercise the data-shape contract without spinning up a real KataGo.
    """
    set_adapter(MockKataGoAdapter())
    import app.services.game_service as gs

    monkeypatch.setattr(gs, "_endgame_phase_from_ownership", lambda *a, **kw: True)

    s = await _make_session(db_session, nickname="es4")
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )

    detail: ScoringDetail = await score_by_request(
        db_session, game=game, session=s
    )

    assert len(detail.ownership) == 9 * 9
    assert all(-1.0 <= v <= 1.0 for v in detail.ownership)

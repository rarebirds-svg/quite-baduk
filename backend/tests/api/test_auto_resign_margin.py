# AI 자동 기권이 집 차이 하한(10집)을 지키는지 검증한다.
"""AI auto-resign must respect the score margin, not just winrate.

The winrate guards (shallow 0.3% → deep 0.1% → 7-turn streak) can all fire
in a close endgame: being 2.5 points behind with no aji left really is a
sub-0.1% position. Resigning there is wrong — humans play those out, and
the user can still misplay the endgame.

These tests pin the fourth guard: the deep read's score lead against the
AI must be at least ``RESIGN_MIN_MARGIN`` points before a losing ply is
allowed to count toward the resign streak.
"""
from __future__ import annotations

import secrets

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.katago.analysis import AnalysisResult
from app.core.katago.mock import MockKataGoAdapter
from app.engine_pool import set_adapter
from app.models import Session
from app.services.game_service import create_game, place_move

# 사용자가 두는 좌표. 목 어댑터는 스캔 순서상 위쪽 줄부터 집으므로
# 아래 두 줄만 쓰면 AI 착점과 겹치지 않는다.
_USER_COORDS = ["A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1", "J1", "A2"]


class _LostButCloseAdapter(MockKataGoAdapter):
    """analyze()의 승률·집 차이를 고정해 자동 기권 경로를 결정적으로 만든다."""

    def __init__(self, *, score_lead: float) -> None:
        super().__init__()
        self._forced_score_lead = score_lead

    async def analyze(
        self, *, side: str = "B", max_visits: int = 100
    ) -> AnalysisResult:
        result = await super().analyze(side=side, max_visits=max_visits)
        # analyze()는 side(=수를 둘 차례인 사용자) 관점이다.
        # 승률 1.0 = 사용자 완승 = AI 승률 0%.
        result.winrate = 1.0
        result.score_lead = self._forced_score_lead
        return result


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


async def _game_past_min_moves(
    db: AsyncSession, *, nickname: str
) -> tuple[Session, object]:
    """최소 수순 게이트(9로반 20수)를 넘긴 대국을 만든다."""
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db, nickname=nickname)
    game = await create_game(
        db,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )
    for coord in _USER_COORDS:
        await place_move(db, game=game, session=s, coord=coord)
    return s, game


@pytest.mark.asyncio
async def test_close_game_does_not_resign_despite_zero_winrate(
    db_session: AsyncSession,
) -> None:
    """2집차 역전 불가 국면이어도 기권하지 않는다 — 끝내기는 두게 둔다."""
    s, game = await _game_past_min_moves(db_session, nickname="closemargin")
    game.loss_streak = 6  # 다음 한 턴이 확정되면 임계(7)에 닿는 상태
    await db_session.commit()

    set_adapter(_LostButCloseAdapter(score_lead=2.0))
    await place_move(db_session, game=game, session=s, coord="B2")

    assert game.status == "active", "2집차에서 기권하면 안 된다"
    # 집 차이 게이트에서 걸렸으므로 연속 카운트도 초기화된다.
    assert (game.loss_streak or 0) == 0


@pytest.mark.asyncio
async def test_hopeless_game_still_resigns(
    db_session: AsyncSession,
) -> None:
    """30집차 완패 국면은 기존대로 기권한다 — 게이트가 정상 경로를 막지 않는다."""
    s, game = await _game_past_min_moves(db_session, nickname="widemargin")
    game.loss_streak = 6
    await db_session.commit()

    set_adapter(_LostButCloseAdapter(score_lead=30.0))
    await place_move(db_session, game=game, session=s, coord="B2")

    assert game.status == "resigned"
    assert game.winner == "user"
    assert game.result == "B+R"

"""대국 소유권 — 세션 직접 소유 또는 같은 연동 계정 소유.

닉네임 세션은 7일 뒤 사라지지만, 구글 계정을 연동해 두면 새 기기·새 세션에서
같은 계정으로 다시 연동했을 때 예전 대국이 그대로 보여야 한다. 그래서 소유
판정은 `session_id` 일치 OR (`account_id`가 있고 세션의 계정과 일치)다.
"""
from __future__ import annotations

from sqlalchemy import ColumnElement, and_, or_

from app.models import Game, Session


def owns(game: Game, sess: Session) -> bool:
    if game.session_id == sess.id:
        return True
    return sess.account_id is not None and game.account_id == sess.account_id


def owned_games_clause(sess: Session) -> ColumnElement[bool]:
    """SELECT ... WHERE 절 — 이 세션이 소유한 대국 전체."""
    if sess.account_id is None:
        return Game.session_id == sess.id
    return or_(
        Game.session_id == sess.id,
        and_(Game.account_id.is_not(None), Game.account_id == sess.account_id),
    )

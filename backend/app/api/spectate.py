# 공개 관전 API — 진행 중/종료된 대국을 소유권 없이 열람하는 엔드포인트
"""공개 관전 엔드포인트 — 소유권 없이 진행 중/종료된 대국을 열람한다.

노출 규칙: 정상 종료(finished/resigned)된 대국, 그리고 아직 세션이
살아있는 진행 중(active) 대국만. active이면서 세션이 사라진 대국은
"버려진 대국"이라 목록·상세 모두에서 제외한다. 관리자 닉네임으로 둔
대국도 닉네임·대국 내용이 노출되지 않도록 전부 숨긴다.

추가 제외: 종료 대국이라도 result가 없거나(승부 미결) 수수가
_MIN_EXPOSED_MOVES 미만이면(즉시 기권 등 사실상 강제 종료) 숨긴다.
시스템 테스트 하네스 닉네임(_TEST_NICKNAME_PREFIXES)의 대국도
진행 중·종료 불문 전부 숨긴다.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import ColumnElement, and_, func, or_, select

from app.deps import ADMIN_NICKNAME_KEYS, CurrentSession, DbSession
from app.models import Game, Move, Session
from app.schemas.datetime_utc import UtcDatetime
from app.schemas.game import GameDetail, GameSummary, MoveEntry

router = APIRouter(prefix="/api/spectate", tags=["spectate"])

_FINISHED = ("finished", "resigned")
# 승부가 성립했다고 볼 최소 수수 — 이보다 짧은 종료 대국(0수 즉시 기권 등)은
# 관전 가치가 없는 강제 종료로 보고 숨긴다.
_MIN_EXPOSED_MOVES = 10
# 시스템 테스트 하네스가 쓰는 닉네임 prefix — 해당 대국은 전부 숨긴다.
# (e2e: qa_*, 스크린샷 캡처: screenshotter*/devshot*)
_TEST_NICKNAME_PREFIXES = ("screenshotter", "devshot", "qa_")


def _prefix_pattern(prefix: str) -> str:
    """LIKE 패턴용 prefix 이스케이프 — 'qa_'의 '_'가 와일드카드로 새지 않게."""
    escaped = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"{escaped}%"


def _not_admin_clause() -> ColumnElement[bool]:
    """관리자 대국 제외 절. 세션이 살아있으면 session.nickname_key로,
    세션이 사라졌으면 games.user_nickname 스냅샷으로 판별한다."""
    keys = list(ADMIN_NICKNAME_KEYS)
    nickname_ok = or_(
        Game.user_nickname.is_(None),
        func.lower(Game.user_nickname).notin_(keys),
    )
    session_ok = or_(
        Game.session_id.is_(None),
        Game.session_id.notin_(
            select(Session.id).where(Session.nickname_key.in_(keys))
        ),
    )
    return and_(nickname_ok, session_ok)


def _not_test_clause() -> ColumnElement[bool]:
    """시스템 테스트 하네스 대국 제외 절. 관리자 제외와 동일하게 세션
    생존 시 nickname_key로, 세션 소멸 시 user_nickname 스냅샷으로 판별."""
    patterns = [_prefix_pattern(p) for p in _TEST_NICKNAME_PREFIXES]
    nickname_ok = or_(
        Game.user_nickname.is_(None),
        and_(
            *[
                func.lower(Game.user_nickname).notlike(pat, escape="\\")
                for pat in patterns
            ]
        ),
    )
    session_ok = or_(
        Game.session_id.is_(None),
        Game.session_id.notin_(
            select(Session.id).where(
                or_(*[Session.nickname_key.like(pat, escape="\\") for pat in patterns])
            )
        ),
    )
    return and_(nickname_ok, session_ok)


def _spectatable_clause() -> ColumnElement[bool]:
    """SQLAlchemy WHERE 절: (승부가 성립한 종료 대국 OR 세션이 살아있는
    진행 중 대국) AND 관리자 대국 아님 AND 테스트 하네스 대국 아님."""
    return and_(
        or_(
            and_(
                Game.status.in_(_FINISHED),
                Game.result.is_not(None),
                Game.move_count >= _MIN_EXPOSED_MOVES,
            ),
            and_(
                Game.status == "active",
                Game.session_id.in_(select(Session.id)),
            ),
        ),
        _not_admin_clause(),
        _not_test_clause(),
    )


class SpectateRow(BaseModel):
    id: int
    user_nickname: str | None
    user_rank: str | None
    user_country: str | None
    ai_player: str | None
    ai_rank: str
    ai_style: str
    board_size: int
    handicap: int
    status: str
    result: str | None
    move_count: int
    started_at: UtcDatetime
    finished_at: UtcDatetime | None
    is_live: bool  # 진행 중(active + 세션 생존)


class SpectateList(BaseModel):
    rows: list[SpectateRow]


@router.get("", response_model=SpectateList)
async def list_spectatable(
    _: CurrentSession,
    db: DbSession,
    limit: int = 50,
) -> SpectateList:
    """관전 가능 대국 목록. 닉네임 세션은 필요하지만 소유권은 불필요.
    진행 중 대국이 위로 오도록 정렬 (started_at 역순)."""
    effective_limit = max(1, min(limit, 100))
    rows = (
        await db.execute(
            select(Game)
            .where(_spectatable_clause())
            .order_by(Game.started_at.desc())
            .limit(effective_limit)
        )
    ).scalars().all()

    return SpectateList(
        rows=[
            SpectateRow(
                id=g.id,
                user_nickname=g.user_nickname,
                user_rank=g.user_rank,
                user_country=g.user_country,
                ai_player=g.ai_player,
                ai_rank=g.ai_rank,
                ai_style=g.ai_style,
                board_size=g.board_size,
                handicap=g.handicap,
                status=g.status,
                result=g.result,
                move_count=g.move_count,
                started_at=g.started_at,
                finished_at=g.finished_at,
                is_live=g.status == "active",
            )
            for g in rows
        ]
    )


@router.get("/{game_id}", response_model=GameDetail)
async def spectate_game(
    game_id: int,
    _: CurrentSession,
    db: DbSession,
) -> GameDetail:
    """관전 가능한 대국의 상세(수순 포함). 필터를 통과하지 못하면 404 —
    버려진 대국·존재하지 않는 대국 모두 동일하게 숨긴다."""
    game = (
        await db.execute(
            select(Game).where(Game.id == game_id, _spectatable_clause())
        )
    ).scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="game_not_found")

    moves = (
        await db.execute(
            select(Move)
            .where(Move.game_id == game.id)
            .order_by(Move.move_number.asc())
        )
    ).scalars().all()
    move_entries = [
        MoveEntry(
            move_number=m.move_number,
            color=m.color,
            coord=m.coord,
            captures=m.captures,
            is_undone=m.is_undone,
        )
        for m in moves
    ]
    base = GameSummary.model_validate(game, from_attributes=True)
    return GameDetail(**base.model_dump(), moves=move_entries)

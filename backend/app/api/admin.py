"""Admin monitoring endpoints. Gated by ``require_admin`` — only the fixed
admin nickname (see ``deps.ADMIN_NICKNAME_KEYS``) can call these."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ws import _connections as _ws_connections
from app.config import settings
from app.deps import get_current_session, get_db, is_admin, require_admin
from app.engine_pool import get_adapter
from app.models import Game, Session, SessionHistory

# Captured at module import so the admin console can show "backend uptime"
# (the FastAPI app itself doesn't expose a boot timestamp).
_BACKEND_STARTED_AT: datetime = datetime.utcnow()

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminSessionRow(BaseModel):
    id: int
    nickname: str
    created_at: datetime
    last_seen_at: datetime
    game_count: int
    active_game_count: int
    is_connected_ws: bool  # currently holding an open WS for at least one game


class AdminGameRow(BaseModel):
    id: int
    session_id: int | None
    nickname: str | None
    status: str
    result: str | None
    winner: str | None  # "user" | "ai" | None — needed so the admin can see
                        # who actually won without decoding the result string
    board_size: int
    handicap: int
    ai_rank: str
    ai_style: str
    ai_player: str | None
    user_rank: str | None
    move_count: int
    undo_count: int
    hint_count: int
    is_live_ws: bool  # true when this specific game currently has an open WS
    started_at: datetime
    finished_at: datetime | None


class AdminIdentity(BaseModel):
    is_admin: bool


class AdminSummary(BaseModel):
    total_games: int
    active_games: int
    finished_games: int
    resigned_games: int
    # AI auto-resign tally — resigns where the user won.
    ai_resigned_games: int
    # Among finished (incl. resigned) games, user win count and rate.
    decisive_games: int
    user_wins: int
    user_win_rate: float
    total_moves: int
    total_undos: int
    total_hints: int
    avg_moves_per_game: float
    live_sessions: int
    live_ws_games: int


class AdminLoginRow(BaseModel):
    id: int
    session_id: int | None
    nickname: str
    created_at: datetime
    ended_at: datetime | None
    end_reason: str | None
    is_active: bool  # currently-open (ended_at IS NULL)


class AdminSessionDetail(BaseModel):
    session: AdminSessionRow | None
    nickname: str
    total_games: int
    active_games: int
    wins: int
    losses: int
    total_moves: int
    total_undos: int
    total_hints: int
    games: list[AdminGameRow]
    history: list[AdminLoginRow]  # all login events for this nickname_key


class AdminEngineHealth(BaseModel):
    mode: str  # "mock" | "real"
    is_alive: bool
    bin_path: str | None
    model_path: str | None
    model_name: str | None
    human_model_path: str | None
    human_model_name: str | None
    config_path: str | None
    backend_started_at: datetime


@router.get("/me", response_model=AdminIdentity)
async def whoami(sess: Session = Depends(get_current_session)) -> AdminIdentity:
    return AdminIdentity(is_admin=is_admin(sess))


@router.get("/summary", response_model=AdminSummary)
async def summary(
    _: Session = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminSummary:
    # Global tallies + status-bucket counts in one grouped query.
    row = (
        await db.execute(
            select(
                func.count(Game.id),
                func.coalesce(
                    func.sum(case((Game.status == "active", 1), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(case((Game.status == "finished", 1), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(case((Game.status == "resigned", 1), else_=0)), 0
                ),
                # AI auto-resign: resigned + user won.
                func.coalesce(
                    func.sum(
                        case(
                            (
                                (Game.status == "resigned")
                                & (Game.winner == "user"),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(func.sum(Game.move_count), 0),
                func.coalesce(func.sum(Game.undo_count), 0),
                func.coalesce(func.sum(Game.hint_count), 0),
            )
        )
    ).one()
    total = int(row[0])
    active = int(row[1])
    finished = int(row[2])
    resigned = int(row[3])
    ai_resigned = int(row[4])
    total_moves = int(row[5])
    total_undos = int(row[6])
    total_hints = int(row[7])

    decisive_row = (
        await db.execute(
            select(
                func.count(Game.id),
                func.coalesce(
                    func.sum(case((Game.winner == "user", 1), else_=0)), 0
                ),
            ).where(Game.status.in_(["finished", "resigned"]))
        )
    ).one()
    decisive = int(decisive_row[0])
    user_wins = int(decisive_row[1])

    live_sessions = len(
        {
            sid for (sid,) in (
                await db.execute(
                    select(Game.session_id).where(
                        Game.id.in_(_ws_connections.keys())
                    )
                )
            ).all()
            if sid is not None
        }
    ) if _ws_connections else 0

    return AdminSummary(
        total_games=total,
        active_games=active,
        finished_games=finished,
        resigned_games=resigned,
        ai_resigned_games=ai_resigned,
        decisive_games=decisive,
        user_wins=user_wins,
        user_win_rate=(user_wins / decisive) if decisive else 0.0,
        total_moves=total_moves,
        total_undos=total_undos,
        total_hints=total_hints,
        avg_moves_per_game=(total_moves / total) if total else 0.0,
        live_sessions=live_sessions,
        live_ws_games=len(_ws_connections),
    )


@router.get("/engine", response_model=AdminEngineHealth)
async def engine(_: Session = Depends(require_admin)) -> AdminEngineHealth:
    if settings.katago_mock:
        return AdminEngineHealth(
            mode="mock",
            is_alive=True,
            bin_path=None,
            model_path=None,
            model_name=None,
            human_model_path=None,
            human_model_name=None,
            config_path=None,
            backend_started_at=_BACKEND_STARTED_AT,
        )
    try:
        adapter = get_adapter()
        alive = bool(getattr(adapter, "is_alive", False))
    except Exception:
        alive = False
    def _basename(p: str | None) -> str | None:
        return Path(p).name if p else None
    return AdminEngineHealth(
        mode="real",
        is_alive=alive,
        bin_path=settings.katago_bin_path,
        model_path=settings.katago_model_path,
        model_name=_basename(settings.katago_model_path),
        human_model_path=settings.katago_human_model_path or None,
        human_model_name=_basename(settings.katago_human_model_path),
        config_path=settings.katago_config_path,
        backend_started_at=_BACKEND_STARTED_AT,
    )


@router.get("/sessions", response_model=list[AdminSessionRow])
async def list_sessions(
    _: Session = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AdminSessionRow]:
    # Count games per session with a single grouped query.
    total_q = (
        select(Game.session_id, func.count(Game.id))
        .group_by(Game.session_id)
    )
    active_q = (
        select(Game.session_id, func.count(Game.id))
        .where(Game.status == "active")
        .group_by(Game.session_id)
    )
    total_rows = {sid: n for sid, n in (await db.execute(total_q)).all()}
    active_rows = {sid: n for sid, n in (await db.execute(active_q)).all()}

    res = await db.execute(
        select(Session).order_by(Session.last_seen_at.desc())
    )
    sessions = res.scalars().all()

    # A session is "connected via WS" if any of its active games has an open
    # websocket. Convert the WS registry (keyed by game_id) into a set of
    # session_ids.
    connected_sids: set[int] = set()
    if _ws_connections:
        live_game_ids = set(_ws_connections.keys())
        if live_game_ids:
            r = await db.execute(
                select(Game.session_id).where(Game.id.in_(live_game_ids))
            )
            connected_sids = {sid for (sid,) in r.all()}

    return [
        AdminSessionRow(
            id=s.id,
            nickname=s.nickname,
            created_at=s.created_at,
            last_seen_at=s.last_seen_at,
            game_count=int(total_rows.get(s.id, 0)),
            active_game_count=int(active_rows.get(s.id, 0)),
            is_connected_ws=s.id in connected_sids,
        )
        for s in sessions
    ]


@router.get("/games", response_model=list[AdminGameRow])
async def list_games(
    status_: str | None = None,
    limit: int = 100,
    _: Session = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AdminGameRow]:
    q = select(Game).order_by(Game.started_at.desc()).limit(max(1, min(limit, 500)))
    if status_:
        q = q.where(Game.status == status_)
    games = (await db.execute(q)).scalars().all()

    sids = {g.session_id for g in games if g.session_id is not None}
    nick_by_sid: dict[int, str] = {}
    if sids:
        sr = await db.execute(select(Session.id, Session.nickname).where(Session.id.in_(sids)))
        nick_by_sid = {sid: nick for sid, nick in sr.all()}

    return [
        AdminGameRow(
            id=g.id,
            session_id=g.session_id,
            # Prefer the snapshot stored at game creation — it survives
            # session deletion, which is the whole point of migration 0008.
            # Fall back to a live session lookup only if the snapshot is
            # missing (legacy rows from before 0007).
            nickname=g.user_nickname
            or (nick_by_sid.get(g.session_id) if g.session_id else None),
            status=g.status,
            result=g.result,
            winner=g.winner,
            board_size=g.board_size,
            handicap=g.handicap,
            ai_rank=g.ai_rank,
            ai_style=g.ai_style,
            ai_player=g.ai_player,
            user_rank=g.user_rank,
            move_count=g.move_count,
            undo_count=g.undo_count,
            hint_count=g.hint_count,
            is_live_ws=g.id in _ws_connections,
            started_at=g.started_at,
            finished_at=g.finished_at,
        )
        for g in games
    ]


@router.get("/login-history", response_model=list[AdminLoginRow])
async def login_history(
    limit: int = 200,
    _: Session = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AdminLoginRow]:
    """Historical login events, newest first. Includes already-ended
    sessions so the admin can see the full connection timeline beyond
    the currently-live `sessions` table."""
    q = (
        select(SessionHistory)
        .order_by(SessionHistory.created_at.desc())
        .limit(max(1, min(limit, 1000)))
    )
    rows = (await db.execute(q)).scalars().all()
    return [
        AdminLoginRow(
            id=r.id,
            session_id=r.session_id,
            nickname=r.nickname,
            created_at=r.created_at,
            ended_at=r.ended_at,
            end_reason=r.end_reason,
            is_active=r.ended_at is None,
        )
        for r in rows
    ]


@router.get("/sessions/{session_id}", response_model=AdminSessionDetail)
async def session_detail(
    session_id: int,
    _: Session = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminSessionDetail:
    """Details for a single session row (if still live) plus every game ever
    played by the same nickname_key — joined across all historical
    sessions so switching logins under the same nickname gives a
    continuous view."""
    live = (
        await db.execute(select(Session).where(Session.id == session_id))
    ).scalar_one_or_none()

    # Resolve the nickname_key to use for games/history lookup. Prefer the
    # live row; fall back to a history row with this session_id so we can
    # still build a detail page after the session is gone.
    nickname: str | None = None
    nickname_key: str | None = None
    if live is not None:
        nickname = live.nickname
        nickname_key = live.nickname_key
    else:
        h = (
            await db.execute(
                select(SessionHistory)
                .where(SessionHistory.session_id == session_id)
                .order_by(SessionHistory.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if h is not None:
            nickname = h.nickname
            nickname_key = h.nickname_key

    if nickname_key is None:
        # Fallback: no live session + no history row — can't show anything.
        return AdminSessionDetail(
            session=None,
            nickname="",
            total_games=0,
            active_games=0,
            wins=0,
            losses=0,
            total_moves=0,
            total_undos=0,
            total_hints=0,
            games=[],
            history=[],
        )

    live_row: AdminSessionRow | None = None
    if live is not None:
        total_games = (
            (await db.execute(
                select(func.count(Game.id)).where(Game.session_id == live.id)
            )).scalar_one() or 0
        )
        active_games = (
            (await db.execute(
                select(func.count(Game.id)).where(
                    Game.session_id == live.id, Game.status == "active"
                )
            )).scalar_one() or 0
        )
        connected_ws = False
        if _ws_connections:
            r = await db.execute(
                select(Game.id).where(Game.id.in_(_ws_connections.keys()),
                                      Game.session_id == live.id)
            )
            connected_ws = r.first() is not None
        live_row = AdminSessionRow(
            id=live.id,
            nickname=live.nickname,
            created_at=live.created_at,
            last_seen_at=live.last_seen_at,
            game_count=int(total_games),
            active_game_count=int(active_games),
            is_connected_ws=connected_ws,
        )

    # Games — key off nickname_key via user_nickname snapshot (for detached
    # games) OR via live session_id. This catches both detached history and
    # currently-live activity under the same nickname.
    game_q = (
        select(Game)
        .where(Game.user_nickname == nickname)
        .order_by(Game.started_at.desc())
        .limit(200)
    )
    games = (await db.execute(game_q)).scalars().all()
    game_rows = [
        AdminGameRow(
            id=g.id,
            session_id=g.session_id,
            nickname=g.user_nickname or nickname,
            status=g.status,
            result=g.result,
            winner=g.winner,
            board_size=g.board_size,
            handicap=g.handicap,
            ai_rank=g.ai_rank,
            ai_style=g.ai_style,
            ai_player=g.ai_player,
            user_rank=g.user_rank,
            move_count=g.move_count,
            undo_count=g.undo_count,
            hint_count=g.hint_count,
            is_live_ws=g.id in _ws_connections,
            started_at=g.started_at,
            finished_at=g.finished_at,
        )
        for g in games
    ]

    agg_row = (
        await db.execute(
            select(
                func.count(Game.id),
                func.coalesce(func.sum(case((Game.status == "active", 1), else_=0)), 0),
                func.coalesce(func.sum(case((Game.winner == "user", 1), else_=0)), 0),
                func.coalesce(func.sum(case((Game.winner == "ai", 1), else_=0)), 0),
                func.coalesce(func.sum(Game.move_count), 0),
                func.coalesce(func.sum(Game.undo_count), 0),
                func.coalesce(func.sum(Game.hint_count), 0),
            ).where(Game.user_nickname == nickname)
        )
    ).one()

    history_rows = (
        await db.execute(
            select(SessionHistory)
            .where(SessionHistory.nickname_key == nickname_key)
            .order_by(SessionHistory.created_at.desc())
            .limit(50)
        )
    ).scalars().all()

    return AdminSessionDetail(
        session=live_row,
        nickname=nickname or "",
        total_games=int(agg_row[0]),
        active_games=int(agg_row[1]),
        wins=int(agg_row[2]),
        losses=int(agg_row[3]),
        total_moves=int(agg_row[4]),
        total_undos=int(agg_row[5]),
        total_hints=int(agg_row[6]),
        games=game_rows,
        history=[
            AdminLoginRow(
                id=r.id,
                session_id=r.session_id,
                nickname=r.nickname,
                created_at=r.created_at,
                ended_at=r.ended_at,
                end_reason=r.end_reason,
                is_active=r.ended_at is None,
            )
            for r in history_rows
        ],
    )

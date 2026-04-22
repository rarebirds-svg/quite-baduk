"""Game lifecycle: create, move, undo, resign, finalize, replay."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.katago.strength import rank_to_config
from app.core.rules.board import BLACK, WHITE
from app.core.rules.engine import (
    GameState,
    IllegalMoveError,
    Move,
    build_sgf,
    is_game_over,
    pass_move,
    play,
    score as score_engine,
)
from app.core.rules.board import Board
from app.core.rules.handicap import HANDICAP_TABLES, apply_handicap
from app.engine_pool import (
    adapter_owner,
    cache_state,
    drop_state,
    game_lock,
    get_adapter,
    get_cached_state,
    set_adapter_owner,
)
from app.models import Game, Move as MoveRow, Session


class GameError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


@dataclass
class MoveResult:
    game_state: GameState
    ai_move: str | None  # coord/"pass"/"resign"/None
    captured_by_user: int
    captured_by_ai: int
    game_over: bool
    result_str: str | None  # "B+R", "W+12.5", etc.
    winrate_black: float | None = None  # side-to-move normalised to Black's winrate


async def _user_side(game: Game) -> str:
    return BLACK if game.user_color == "black" else WHITE


def _ai_side(game: Game) -> str:
    return WHITE if game.user_color == "black" else BLACK


async def create_game(
    db: AsyncSession,
    *,
    session: Session,
    ai_rank: str,
    handicap: int,
    user_color: str,
    board_size: int,
    ai_style: str = "balanced",
    ai_player: str | None = None,
) -> Game:
    if board_size not in HANDICAP_TABLES:
        raise GameError("INVALID_BOARD_SIZE", str(board_size))
    valid_handicaps = (0,) + tuple(HANDICAP_TABLES[board_size].keys())
    if handicap not in valid_handicaps:
        raise GameError("INVALID_HANDICAP", str(handicap))
    if user_color not in ("black", "white"):
        raise GameError("INVALID_COLOR", user_color)
    komi = 0.5 if handicap > 0 else 6.5
    if handicap > 0:
        user_color = "black"

    # If a specific player is chosen, derive the style from the player so
    # the two fields stay consistent and summaries/reseeds don't disagree.
    from app.core.katago.players import get_player

    resolved_player = get_player(ai_player)
    resolved_style = resolved_player.style if resolved_player else ai_style

    game = Game(
        session_id=session.id,
        ai_rank=ai_rank,
        ai_style=resolved_style,
        ai_player=ai_player if resolved_player else None,
        handicap=handicap,
        board_size=board_size,
        komi=komi,
        user_color=user_color,
        status="active",
    )
    db.add(game)
    await db.commit()
    await db.refresh(game)

    adapter = get_adapter()
    await adapter.start()
    await adapter.set_boardsize(board_size)
    await adapter.set_komi(komi)
    cfg = rank_to_config(ai_rank, resolved_style, game.ai_player)
    await adapter.set_profile(cfg)

    state = GameState(board=Board(board_size), komi=komi)
    if handicap > 0:
        state.board = apply_handicap(state.board, handicap)
        for coord in HANDICAP_TABLES[board_size][handicap]:
            await adapter.play(BLACK, coord)
        state.to_move = WHITE

    cache_state(game.id, state)
    set_adapter_owner(game.id)
    return game


async def _record_move(
    db: AsyncSession, *, game_id: int, move_number: int, color: str, coord: str | None, captures: int
) -> None:
    stored_coord = coord if coord != "resign" else None
    db.add(MoveRow(
        game_id=game_id,
        move_number=move_number,
        color=color,
        coord=stored_coord,
        captures=captures,
    ))


async def place_move(
    db: AsyncSession, *, game: Game, session: Session, coord: str
) -> MoveResult:
    if game.session_id != session.id:
        raise GameError("FORBIDDEN", "game.session_id != session.id")
    if game.status != "active":
        raise GameError("GAME_NOT_ACTIVE", game.status)

    state = get_cached_state(game.id)
    if state is None:
        state = await _replay_state(db, game)
        cache_state(game.id, state)

    adapter = get_adapter()
    user_side = BLACK if game.user_color == "black" else WHITE
    ai_side = WHITE if user_side == BLACK else BLACK

    # Lock per game
    async with game_lock(game.id):
        # Validate + apply user move
        try:
            new_state = play(state, Move(color=user_side, coord=coord))  # type: ignore[arg-type]
        except IllegalMoveError as e:
            raise GameError(e.code, e.detail)

        # Figure out captures by user
        user_captures = new_state.captures.get(user_side, 0) - state.captures.get(user_side, 0)

        # Persist user move
        move_no = game.move_count + 1
        await _record_move(
            db, game_id=game.id, move_number=move_no, color=user_side, coord=coord, captures=user_captures,
        )
        game.move_count = move_no

        # Sync the shared KataGo adapter with the rules state (including the
        # user's latest move). The adapter is process-wide, so its internal
        # board can drift whenever the user switches between games or the
        # subprocess restarts; without this step KataGo may return a coord
        # that the rules engine rejects as AI_ILLEGAL_MOVE.
        await _sync_adapter(game, state, new_state, coord)

        ai_move: str | None = None
        ai_captures = 0
        game_over = False
        result_str: str | None = None

        if is_game_over(new_state):
            # two passes -> finalize
            await _finalize_game(db, game, new_state)
            game_over = True
            result_str = game.result
        else:
            # AI responds
            ai_move = await adapter.genmove(ai_side)
            prev_captures_ai = new_state.captures.get(ai_side, 0)
            try:
                if ai_move.lower() == "resign":
                    game.status = "resigned"
                    game.winner = "user"
                    game.result = f"{user_side}+R"
                    result_str = game.result
                    game_over = True
                elif ai_move.lower() == "pass":
                    new_state = pass_move(new_state, ai_side)  # type: ignore[arg-type]
                else:
                    new_state = play(new_state, Move(color=ai_side, coord=ai_move))  # type: ignore[arg-type]
            except IllegalMoveError as e:
                raise GameError("AI_ILLEGAL_MOVE", f"{ai_move}: {e}")

            ai_captures = new_state.captures.get(ai_side, 0) - prev_captures_ai
            if not game_over:
                move_no += 1
                await _record_move(
                    db, game_id=game.id, move_number=move_no, color=ai_side,
                    coord=(None if ai_move.lower() == "resign" else ai_move),
                    captures=ai_captures,
                )
                game.move_count = move_no
                if is_game_over(new_state):
                    await _finalize_game(db, game, new_state)
                    game_over = True
                    result_str = game.result

        await db.commit()
        cache_state(game.id, new_state)

        # Compute a cheap position evaluation so the UI can show the live
        # winrate after each move. Swallow failures — winrate is optional.
        winrate_black: float | None = None
        if not game_over:
            try:
                analysis = await adapter.analyze(side=new_state.to_move, max_visits=32)
                wr = float(analysis.winrate)
                # analyze() returns the winrate from the side-to-move's perspective.
                winrate_black = wr if new_state.to_move == BLACK else 1.0 - wr
            except Exception:
                winrate_black = None

        return MoveResult(
            game_state=new_state,
            ai_move=ai_move,
            captured_by_user=user_captures,
            captured_by_ai=ai_captures,
            game_over=game_over,
            result_str=result_str,
            winrate_black=winrate_black,
        )


async def undo_move(db: AsyncSession, *, game: Game, session: Session, steps: int = 2) -> GameState:
    if game.session_id != session.id:
        raise GameError("FORBIDDEN")
    if game.status != "active":
        raise GameError("GAME_NOT_ACTIVE", game.status)
    if steps < 1:
        raise GameError("INVALID_UNDO_STEPS")

    async with game_lock(game.id):
        # Mark the last N non-undone moves as undone
        res = await db.execute(
            select(MoveRow).where(MoveRow.game_id == game.id, MoveRow.is_undone == False).order_by(MoveRow.move_number.desc())  # noqa: E712
        )
        rows = res.scalars().all()
        to_undo = rows[:steps]
        if not to_undo:
            raise GameError("NO_MOVES_TO_UNDO")
        for row in to_undo:
            row.is_undone = True
            game.move_count -= 1

        # Force the next place_move to fully reseed the shared adapter — this
        # is cheaper and more reliable than trying to keep adapter.undo() in
        # lockstep with a multi-step undo that straddles captures.
        set_adapter_owner(None)

        state = await _replay_state(db, game)
        cache_state(game.id, state)
        await db.commit()
        return state


async def resign_game(db: AsyncSession, *, game: Game, session: Session) -> Game:
    if game.session_id != session.id:
        raise GameError("FORBIDDEN")
    if game.status != "active":
        raise GameError("GAME_NOT_ACTIVE", game.status)
    game.status = "resigned"
    game.winner = "ai"
    game.result = ("W+R" if game.user_color == "black" else "B+R")
    state = get_cached_state(game.id) or await _replay_state(db, game)
    game.sgf_cache = build_sgf(state, result=game.result)
    await db.commit()
    return game


async def _finalize_game(db: AsyncSession, game: Game, state: GameState) -> None:
    # Compute territory using the rules engine (auto, no dead-stone input)
    result = score_engine(state)
    margin = result.margin
    prefix = "B+" if result.winner == BLACK else "W+"
    game.status = "finished"
    game.winner = "user" if (
        (result.winner == BLACK and game.user_color == "black") or
        (result.winner == WHITE and game.user_color == "white")
    ) else "ai"
    game.result = f"{prefix}{margin:g}"
    game.sgf_cache = build_sgf(state, result=game.result)
    import datetime as _dt
    game.finished_at = _dt.datetime.now(_dt.timezone.utc)


async def _replay_state(db: AsyncSession, game: Game) -> GameState:
    """Rebuild GameState by replaying non-undone moves."""
    state = GameState(board=Board(game.board_size), komi=game.komi)
    if game.handicap > 0:
        state.board = apply_handicap(state.board, game.handicap)
        state.to_move = WHITE
    res = await db.execute(
        select(MoveRow).where(MoveRow.game_id == game.id, MoveRow.is_undone == False).order_by(MoveRow.move_number.asc())  # noqa: E712
    )
    for m in res.scalars().all():
        coord = m.coord if m.coord else "pass"
        state = play(state, Move(color=m.color, coord=coord))  # type: ignore[arg-type]
    return state


async def _reseed_adapter(game: Game, state: GameState) -> None:
    """Reset the shared KataGo adapter so its internal board matches ``state``.

    The adapter is a single process-wide subprocess, so switching between
    games or recovering from a restart can leave its board out of sync with
    the rules engine. Without this step, KataGo may genmove a coord that
    is out of bounds or otherwise illegal in the current game's rules
    state, and we surface it to the user as ``AI_ILLEGAL_MOVE``.
    """
    adapter = get_adapter()
    await adapter.start()
    await adapter.set_boardsize(game.board_size)
    await adapter.set_komi(game.komi)
    cfg = rank_to_config(
        game.ai_rank,
        getattr(game, "ai_style", "balanced"),
        getattr(game, "ai_player", None),
    )
    await adapter.set_profile(cfg)
    # Handicap stones first (they're placed directly on the board and are not
    # in move_history).
    if game.handicap > 0:
        for hcoord in HANDICAP_TABLES[game.board_size][game.handicap]:
            await adapter.play(BLACK, hcoord)
    # Then replay the game's move history.
    for mv in state.move_history:
        if mv.coord is None:
            continue  # resign — no board change
        await adapter.play(mv.color, mv.coord)
    set_adapter_owner(game.id)


async def _sync_adapter(
    game: Game,
    state_before_user: GameState,
    new_state: GameState,
    user_move_coord: str,
) -> None:
    """Bring the shared adapter in sync with ``new_state``.

    Fast path: the adapter already owns this game, so we just play the user's
    latest move on top of what's already loaded.

    Slow path: ownership differs (another game interleaved, or the process
    restarted) — wipe and replay the full history.
    """
    if adapter_owner() == game.id:
        adapter = get_adapter()
        await adapter.start()
        await adapter.play(
            BLACK if game.user_color == "black" else WHITE,
            user_move_coord,
        )
        return
    await _reseed_adapter(game, new_state)


async def hint(game: Game, side: str, max_visits: int = 50) -> list[Any]:
    adapter = get_adapter()
    await adapter.start()
    analysis = await adapter.analyze(side=side, max_visits=max_visits)
    return analysis.top_moves[:3]


async def analyze_position(game: Game, side: str, max_visits: int = 100) -> Any:
    adapter = get_adapter()
    await adapter.start()
    return await adapter.analyze(side=side, max_visits=max_visits)

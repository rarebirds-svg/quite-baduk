"""Game lifecycle: create, move, undo, resign, finalize, replay."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.katago.strength import rank_to_config
from app.core.rules.board import BLACK, EMPTY, WHITE, Board
from app.core.rules.engine import (
    GameState,
    IllegalMoveError,
    Move,
    build_sgf,
    is_game_over,
    pass_move,
    play,
)
from app.core.rules.engine import (
    score as score_engine,
)
from app.core.rules.handicap import HANDICAP_TABLES, apply_handicap
from app.engine_pool import (
    adapter_owner,
    cache_state,
    game_lock,
    get_adapter,
    get_cached_state,
    set_adapter_owner,
)
from app.models import Game, Session
from app.models import Move as MoveRow


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
    score_lead_black: float | None = None  # positive = black ahead, negative = white ahead
    endgame_phase: bool = False  # true when dame-fill phase detected (score-by-request eligible)
    # Populated when the AI unilaterally passes in a settled position — the
    # service has already run the scoring logic and finalized the game.
    ai_passed_scored: ScoringDetail | None = None


@dataclass
class ScoringDetail:
    """Per-side breakdown returned by the "계가 신청" (request scoring) flow."""
    black_territory: int
    white_territory: int
    black_captures: int
    white_captures: int
    komi: float
    black_score: float
    white_score: float
    winner: str  # 'B' or 'W'
    margin: float
    result_str: str  # "B+3.5"
    black_points: frozenset[tuple[int, int]] = frozenset()
    white_points: frozenset[tuple[int, int]] = frozenset()
    dame_points: frozenset[tuple[int, int]] = frozenset()
    dead_stones: frozenset[tuple[int, int]] = frozenset()


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
    user_rank: str | None = None,
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
        user_nickname=session.nickname,
        user_rank=user_rank,
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
    db: AsyncSession,
    *,
    game_id: int,
    move_number: int,
    color: str,
    coord: str | None,
    captures: int,
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
    db: AsyncSession,
    *,
    game: Game,
    session: Session,
    coord: str,
    on_user_applied: Callable[[GameState, int], Awaitable[None]] | None = None,
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
        # Back-compat self-heal. Games created before the "delete on undo"
        # fix have is_undone=True rows sitting in the moves table — those
        # collide with the UNIQUE(game_id, move_number) constraint on the
        # next INSERT. Purge them up front so those games can still be
        # played instead of raising IntegrityError forever.
        await db.execute(
            delete(MoveRow).where(
                MoveRow.game_id == game.id, MoveRow.is_undone.is_(True)
            )
        )
        # Validate + apply user move
        try:
            new_state = play(state, Move(color=user_side, coord=coord))
        except IllegalMoveError as e:
            raise GameError(e.code, e.detail) from e

        # Figure out captures by user
        user_captures = new_state.captures.get(user_side, 0) - state.captures.get(user_side, 0)

        # Persist user move
        move_no = game.move_count + 1
        await _record_move(
            db,
            game_id=game.id,
            move_number=move_no,
            color=user_side,
            coord=coord,
            captures=user_captures,
        )
        game.move_count = move_no

        # Sync the shared KataGo adapter with the rules state (including the
        # user's latest move). The adapter is process-wide, so its internal
        # board can drift whenever the user switches between games or the
        # subprocess restarts; without this step KataGo may return a coord
        # that the rules engine rejects as AI_ILLEGAL_MOVE.
        await _sync_adapter(game, state, new_state, coord)

        # Flush the user's move to the client before the AI starts thinking.
        # Captures take effect in `new_state` above; without this hook the
        # user would wait on `genmove` before seeing their own stones disappear.
        if on_user_applied is not None:
            await on_user_applied(new_state, user_captures)

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
                    new_state = pass_move(new_state, ai_side)
                else:
                    new_state = play(new_state, Move(color=ai_side, coord=ai_move))
            except IllegalMoveError as e:
                raise GameError("AI_ILLEGAL_MOVE", f"{ai_move}: {e}") from e

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
        # winrate + score lead + endgame phase after each move. Swallow
        # failures — eval is optional. Also reused to decide whether the AI
        # should resign on its next read.
        winrate_black: float | None = None
        score_lead_black: float | None = None
        endgame_phase = False
        if not game_over:
            try:
                analysis = await adapter.analyze(side=new_state.to_move, max_visits=32)
                wr = float(analysis.winrate)
                sl = float(analysis.score_lead)
                # analyze() reports both from the side-to-move's perspective.
                winrate_black = wr if new_state.to_move == BLACK else 1.0 - wr
                score_lead_black = sl if new_state.to_move == BLACK else -sl
                endgame_phase = _endgame_phase_from_ownership(
                    new_state, analysis.ownership
                )

                # AI auto-resign — three guards to prevent premature
                # resigns from noisy 32-visit winrate reads (especially
                # on 9x9 where a single capture can swing 20%+):
                #
                #   1. Min-move gate: ≥ 2×board_size ply played. 9x9 = 20,
                #      19x19 = 40. Below this, winrate reads are too
                #      unstable to trust.
                #   2. Two-stage eval: the 32-visit shallow read serves as
                #      a *trigger* (< 3%), not a decision. A deeper
                #      200-visit re-analysis must agree (< 1%).
                #   3. Loss-streak: the deep-confirmed sub-1% condition
                #      must hold for three consecutive AI turns. One
                #      noisy read can't end the game; the user has plies
                #      in between to play into a recovery. Persisted in
                #      games.loss_streak so it survives reconnects.
                ai_winrate_shallow = 1.0 - wr
                resign_min_moves = max(20, new_state.board.size * 2)
                is_normal_ai_move = (
                    ai_move is not None
                    and ai_move.lower() not in ("pass", "resign")
                )
                deep_confirms_loss = False
                if (
                    is_normal_ai_move
                    and len(new_state.move_history) >= resign_min_moves
                    and ai_winrate_shallow < 0.03
                ):
                    try:
                        deep = await adapter.analyze(
                            side=new_state.to_move, max_visits=200
                        )
                        deep_ai_wr = 1.0 - float(deep.winrate)
                    except Exception:
                        deep_ai_wr = 1.0
                    deep_confirms_loss = deep_ai_wr < 0.01

                if deep_confirms_loss:
                    game.loss_streak = (game.loss_streak or 0) + 1
                elif is_normal_ai_move:
                    # Reset streak on any AI turn that isn't confirming a
                    # crushing loss. Streak only reflects consecutive
                    # deep-confirmed losing ply.
                    if game.loss_streak:
                        game.loss_streak = 0

                RESIGN_STREAK_THRESHOLD = 3
                if game.loss_streak >= RESIGN_STREAK_THRESHOLD:
                    game.status = "resigned"
                    game.winner = "user"
                    game.result = f"{user_side}+R"
                    result_str = game.result
                    game_over = True
                    game.sgf_cache = build_sgf(new_state, result=game.result)
                    import datetime as _dt
                    game.finished_at = _dt.datetime.now(_dt.UTC)
                    await db.commit()
            except Exception:
                winrate_black = None
                score_lead_black = None
                endgame_phase = False

        # AI unilateral pass in a settled position: the AI is effectively
        # saying "the game is over, let's score". Run the same scoring
        # pipeline as a manual /score_request and finalize the game.
        ai_passed_scored: ScoringDetail | None = None
        if (
            not game_over
            and ai_move is not None
            and ai_move.lower() == "pass"
            and endgame_phase
        ):
            try:
                # Re-use the analysis we already ran for ownership.
                dead_stones = _dead_stones_from_ownership(new_state, analysis.ownership)
                result_obj = score_engine(new_state, dead_stones=dead_stones)
                margin = result_obj.margin
                prefix = "B+" if result_obj.winner == BLACK else "W+"
                result_str_local = f"{prefix}{margin:g}"

                game.status = "finished"
                game.winner = "user" if (
                    (result_obj.winner == BLACK and game.user_color == "black")
                    or (result_obj.winner == WHITE and game.user_color == "white")
                ) else "ai"
                game.result = result_str_local
                game.sgf_cache = build_sgf(new_state, result=result_str_local)
                import datetime as _dt
                game.finished_at = _dt.datetime.now(_dt.UTC)
                await db.commit()

                game_over = True
                result_str = result_str_local
                ai_passed_scored = ScoringDetail(
                    black_territory=result_obj.black_territory,
                    white_territory=result_obj.white_territory,
                    black_captures=result_obj.black_captures,
                    white_captures=result_obj.white_captures,
                    komi=result_obj.komi,
                    black_score=result_obj.black_score,
                    white_score=result_obj.white_score,
                    winner=result_obj.winner,
                    margin=result_obj.margin,
                    result_str=result_str_local,
                    black_points=result_obj.black_points,
                    white_points=result_obj.white_points,
                    dame_points=result_obj.dame_points,
                    dead_stones=frozenset(dead_stones),
                )
            except Exception:
                # If anything fails we leave the game open; the pass is
                # still recorded and the user can play on or pass too.
                ai_passed_scored = None

        return MoveResult(
            game_state=new_state,
            ai_move=ai_move,
            captured_by_user=user_captures,
            captured_by_ai=ai_captures,
            game_over=game_over,
            result_str=result_str,
            winrate_black=winrate_black,
            score_lead_black=score_lead_black,
            endgame_phase=endgame_phase,
            ai_passed_scored=ai_passed_scored,
        )


UNDO_LIMIT = 3


async def undo_move(db: AsyncSession, *, game: Game, session: Session, steps: int = 2) -> GameState:
    if game.session_id != session.id:
        raise GameError("FORBIDDEN")
    if game.status != "active":
        raise GameError("GAME_NOT_ACTIVE", game.status)
    if steps < 1:
        raise GameError("INVALID_UNDO_STEPS")
    if game.undo_count >= UNDO_LIMIT:
        raise GameError("UNDO_LIMIT_EXCEEDED", f"max {UNDO_LIMIT} undos per game")

    async with game_lock(game.id):
        # Delete the last N moves outright. Marking is_undone=True is
        # tempting for audit purposes, but the moves table has a
        # UNIQUE(game_id, move_number) constraint — a ghost row would
        # collide with the next place_move's INSERT and brick the game.
        res = await db.execute(
            select(MoveRow)
            .where(MoveRow.game_id == game.id, MoveRow.is_undone.is_(False))
            .order_by(MoveRow.move_number.desc())
        )
        rows = res.scalars().all()
        to_undo = rows[:steps]
        if not to_undo:
            raise GameError("NO_MOVES_TO_UNDO")
        for row in to_undo:
            await db.delete(row)
            game.move_count -= 1
        game.undo_count += 1

        # Force the next place_move to fully reseed the shared adapter — this
        # is cheaper and more reliable than trying to keep adapter.undo() in
        # lockstep with a multi-step undo that straddles captures.
        set_adapter_owner(None)

        state = await _replay_state(db, game)
        cache_state(game.id, state)
        await db.commit()
        return state


async def score_by_request(
    db: AsyncSession, *, game: Game, session: Session
) -> ScoringDetail:
    """Finalize the game "계가 신청" style — auto dead-stone, Korean territory
    scoring, full per-side breakdown. Rejects if the position isn't in the
    yose/dame-fill phase yet, so a user can't short-circuit an unsettled game."""
    if game.session_id != session.id:
        raise GameError("FORBIDDEN")
    if game.status != "active":
        raise GameError("GAME_NOT_ACTIVE", game.status)

    state = get_cached_state(game.id) or await _replay_state(db, game)
    adapter = get_adapter()
    await adapter.start()

    # Deeper analysis than the mid-game 32-visit read — we need a confident
    # ownership read for both phase gating and dead-stone inference.
    try:
        analysis = await adapter.analyze(side=state.to_move, max_visits=200)
    except Exception as e:
        raise GameError("ANALYSIS_FAILED", str(e)) from e

    if not _endgame_phase_from_ownership(state, analysis.ownership):
        raise GameError(
            "NOT_IN_ENDGAME_PHASE",
            "The position is not settled enough to score yet.",
        )

    async with game_lock(game.id):
        dead_stones = _dead_stones_from_ownership(state, analysis.ownership)
        result = score_engine(state, dead_stones=dead_stones)
        margin = result.margin
        prefix = "B+" if result.winner == BLACK else "W+"
        result_str = f"{prefix}{margin:g}"

        game.status = "finished"
        game.winner = "user" if (
            (result.winner == BLACK and game.user_color == "black")
            or (result.winner == WHITE and game.user_color == "white")
        ) else "ai"
        game.result = result_str
        game.sgf_cache = build_sgf(state, result=result_str)
        import datetime as _dt
        game.finished_at = _dt.datetime.now(_dt.UTC)
        await db.commit()

    return ScoringDetail(
        black_territory=result.black_territory,
        white_territory=result.white_territory,
        black_captures=result.black_captures,
        white_captures=result.white_captures,
        komi=result.komi,
        black_score=result.black_score,
        white_score=result.white_score,
        winner=result.winner,
        margin=result.margin,
        result_str=result_str,
        black_points=result.black_points,
        white_points=result.white_points,
        dame_points=result.dame_points,
        dead_stones=frozenset(dead_stones),
    )


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


# Ownership threshold: a stone is considered dead when the ownership value at
# that point has the opposite sign of the stone's color with at least this
# magnitude. KataGo ownership is +1 for definitely Black, -1 for definitely
# White; values near 0 are contested. 0.6 is conservative — it won't demote
# live groups, but it may miss some marginal cases (which we then under-count
# rather than hand points to the wrong side).
_DEAD_STONE_OWNERSHIP_THRESHOLD = 0.6


def _endgame_phase_from_ownership(state: GameState, ownership: list[float]) -> bool:
    """True when the position is firmly resolved — stones are clearly alive or
    dead, and few empty points remain contested. Used to gate the "계가 신청"
    button so it can't be pressed while the board is still in flux.

    Thresholds tuned for real games: initial constants were too strict and
    almost never fired on 9x9/13x13 even in obviously-settled positions.
    """
    size = state.board.size
    if len(ownership) != size * size:
        return False
    # Require SOME play before declaring endgame — avoid flagging an empty
    # fuseki board. Scaled linearly with board size; 9x9 ≥ 9 moves,
    # 13x13 ≥ 13, 19x19 ≥ 19.
    if len(state.move_history) < size:
        return False
    empty_contested = 0
    stone_unsettled = 0
    for y in range(size):
        for x in range(size):
            cell = state.board.get(x, y)
            val = ownership[y * size + x]
            if cell == EMPTY:
                # |ownership| < 0.35 ~= still contested. Above that, the
                # point has leaned one side strongly enough to call it
                # resolved even if not yet a stone.
                if abs(val) < 0.35:
                    empty_contested += 1
            else:
                # Stone whose color disagrees with ownership is "unsettled"
                # (could still die or live). Tight threshold prevents false
                # endgames on fighting positions.
                if cell == BLACK and val < 0.1:
                    stone_unsettled += 1
                elif cell == WHITE and val > -0.1:
                    stone_unsettled += 1
    # Budget for "contested empty" points — roughly a third of each board
    # dimension, with a floor of 6. Realistic games still have several
    # contested dame points when players are ready to score.
    contested_budget = max(6, size // 3 * 2)
    # Allow a small number of unsettled stones (one weak group on the
    # board shouldn't block scoring in practice).
    unsettled_budget = max(0, size // 6)
    return empty_contested <= contested_budget and stone_unsettled <= unsettled_budget


def _dead_stones_from_ownership(
    state: GameState, ownership: list[float]
) -> set[tuple[int, int]]:
    """Pure version — takes an already-fetched ownership vector and marks stones
    whose position is owned by the opposite color beyond the confidence
    threshold. Ownership convention: +1 = definitely Black, -1 = definitely
    White. Our Board uses y=0 at top, matching KataGo's row-major ordering."""
    size = state.board.size
    if len(ownership) != size * size:
        return set()
    dead: set[tuple[int, int]] = set()
    for y in range(size):
        for x in range(size):
            cell = state.board.get(x, y)
            if cell not in (BLACK, WHITE):
                continue
            val = ownership[y * size + x]
            if cell == BLACK and val < -_DEAD_STONE_OWNERSHIP_THRESHOLD:
                dead.add((x, y))
            elif cell == WHITE and val > _DEAD_STONE_OWNERSHIP_THRESHOLD:
                dead.add((x, y))
    return dead


async def _infer_dead_stones(state: GameState) -> set[tuple[int, int]]:
    """Run a fresh KataGo analysis and return dead stones. Returns empty on
    any analysis failure."""
    from app.engine_pool import get_adapter

    try:
        adapter = get_adapter()
        await adapter.start()
        analysis = await adapter.analyze(side=state.to_move, max_visits=200)
    except Exception:
        return set()
    return _dead_stones_from_ownership(state, analysis.ownership)


async def _finalize_game(db: AsyncSession, game: Game, state: GameState) -> None:
    # Ask KataGo for an ownership read, then convert it to a dead-stone set so
    # scoring can reflect obviously-captured groups that both players passed
    # over without physically removing. We use a strong threshold so live
    # groups are never demoted — any false positive would hand opponent points.
    dead_stones = await _infer_dead_stones(state)
    result = score_engine(state, dead_stones=dead_stones)
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
    game.finished_at = _dt.datetime.now(_dt.UTC)


async def _replay_state(db: AsyncSession, game: Game) -> GameState:
    """Rebuild GameState by replaying non-undone moves."""
    state = GameState(board=Board(game.board_size), komi=game.komi)
    if game.handicap > 0:
        state.board = apply_handicap(state.board, game.handicap)
        state.to_move = WHITE
    res = await db.execute(
        select(MoveRow)
        .where(MoveRow.game_id == game.id, MoveRow.is_undone == False)  # noqa: E712
        .order_by(MoveRow.move_number.asc())
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
    # Always wipe the subprocess board first. set_boardsize (= GTP `boardsize`)
    # is documented to clear, but some KataGo builds leave the previous
    # position untouched when the size matches — which surfaces as
    # "illegal move" during the replay below since the stones from a prior
    # game are still on the board.
    await adapter.clear_board()
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


async def hint(
    game: Game, state: GameState, side: str, max_visits: int = 50
) -> list[Any]:
    # The shared adapter's internal board can drift from this game's rules
    # state (another game interleaved, the subprocess restarted, or an undo
    # just reset ownership). Reseed when we don't own it so hints reflect
    # the actual position and not a stale one from a different game.
    if adapter_owner() != game.id:
        await _reseed_adapter(game, state)
    adapter = get_adapter()
    await adapter.start()
    analysis = await adapter.analyze(side=side, max_visits=max_visits)
    return analysis.top_moves[:3]


async def analyze_position(game: Game, side: str, max_visits: int = 100) -> Any:
    adapter = get_adapter()
    await adapter.start()
    return await adapter.analyze(side=side, max_visits=max_visits)

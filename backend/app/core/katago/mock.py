"""MockKataGoAdapter: deterministic GTP-compatible stand-in for tests and dev.

Must stay board-consistent with the rules engine: it applies captures on every
play and refuses to genmove suicides or ko violations, otherwise the service
layer would raise ``AI_ILLEGAL_MOVE`` for moves that the rules engine rejects
on replay.
"""

from __future__ import annotations

from app.core.katago.adapter import GTPResult
from app.core.katago.analysis import AnalysisResult, MoveHint
from app.core.katago.strength import StrengthConfig
from app.core.rules.board import BLACK, WHITE, Board
from app.core.rules.captures import is_suicide, place_with_captures
from app.core.rules.ko import KoState, is_ko_violation
from app.core.rules.sgf_coord import gtp_to_xy, xy_to_gtp


class MockKataGoAdapter:
    """Drop-in replacement for KataGoAdapter."""

    def __init__(self) -> None:
        self.board_size = 19
        self.board = Board(self.board_size)
        self.komi = 6.5
        self.profile: tuple[str, int] | None = None
        self.move_history: list[tuple[str, str]] = []
        self._ko_state = KoState()
        self._started = False

    @property
    def is_alive(self) -> bool:
        return self._started

    async def start(self) -> None:
        self._started = True

    async def stop(self) -> None:
        self._started = False

    async def send(self, cmd: str, timeout: float | None = None) -> GTPResult:
        return GTPResult(ok=True, body="")

    async def clear_board(self) -> None:
        self.board = Board(self.board_size)
        self.move_history.clear()
        self._ko_state = KoState()

    async def set_boardsize(self, size: int) -> None:
        self.board_size = size
        self.board = Board(size)
        self.move_history.clear()
        self._ko_state = KoState()

    async def set_komi(self, komi: float) -> None:
        self.komi = komi

    async def set_profile(self, profile_or_config: StrengthConfig | str, max_visits: int | None = None) -> None:
        if isinstance(profile_or_config, StrengthConfig):
            self.profile = (profile_or_config.human_sl_profile, profile_or_config.max_visits)
        else:
            assert max_visits is not None
            self.profile = (profile_or_config, max_visits)

    async def play(self, color: str, coord: str) -> None:
        if coord.lower() == "pass":
            self.move_history.append((color, "pass"))
            self._ko_state = self._ko_state.update(self.board)
            return
        xy = gtp_to_xy(coord, self.board_size)
        if xy is None:
            return
        x, y = xy
        if not self.board.is_empty(x, y):
            return  # tolerate: real GTP would error, we just ignore
        prev_board = self.board
        new_board, _captured = place_with_captures(self.board, x, y, color)
        self.board = new_board
        self._ko_state = KoState(previous_board=prev_board)
        self.move_history.append((color, coord))

    async def undo(self) -> None:
        if not self.move_history:
            return
        self.move_history.pop()
        # Rebuild from remaining history so captures are re-applied correctly.
        history = list(self.move_history)
        self.board = Board(self.board_size)
        self._ko_state = KoState()
        self.move_history = []
        for c, co in history:
            await self.play(c, co)

    async def genmove(self, color: str) -> str:
        # Scan deterministically top-left → bottom-right, skip any cell that
        # would be rejected by the rules engine (occupied / suicide / ko).
        for y in range(self.board_size):
            for x in range(self.board_size):
                if not self.board.is_empty(x, y):
                    continue
                if is_suicide(self.board, x, y, color):
                    continue
                candidate_board, _ = place_with_captures(self.board, x, y, color)
                if is_ko_violation(self._ko_state, candidate_board):
                    continue
                coord = xy_to_gtp(x, y, self.board_size)
                await self.play(color, coord)
                return coord
        return "pass"

    async def final_score(self) -> str:
        # Deterministic placeholder
        return "B+0.5"

    async def analyze(self, *, side: str = "B", max_visits: int = 100) -> AnalysisResult:
        # Pick up to 3 legal candidates in scan order as hints.
        hints: list[MoveHint] = []
        for y in range(self.board_size):
            if len(hints) >= 3:
                break
            for x in range(self.board_size):
                if len(hints) >= 3:
                    break
                if not self.board.is_empty(x, y):
                    continue
                if is_suicide(self.board, x, y, side):
                    continue
                coord = xy_to_gtp(x, y, self.board_size)
                hints.append(
                    MoveHint(
                        move=coord,
                        visits=max_visits - len(hints) * 10,
                        winrate=0.5 + len(hints) * 0.01,
                    )
                )

        # Heuristic side-to-move winrate: stone-count differential on the
        # current board, normalised to [0.05, 0.95]. Good enough for mock-mode
        # dev; real KataGo returns a real winrate.
        total = self.board_size * self.board_size
        b_count = sum(
            1
            for yy in range(self.board_size)
            for xx in range(self.board_size)
            if self.board.get(xx, yy) == BLACK
        )
        w_count = sum(
            1
            for yy in range(self.board_size)
            for xx in range(self.board_size)
            if self.board.get(xx, yy) == WHITE
        )
        diff = (b_count - w_count) if side == BLACK else (w_count - b_count)
        raw = 0.5 + diff / max(total, 1)
        winrate = max(0.05, min(0.95, raw))

        return AnalysisResult(
            top_moves=hints,
            ownership=[0.0] * (self.board_size * self.board_size),
            winrate=winrate,
        )

    async def version(self) -> str:
        return "Mock 1.0"

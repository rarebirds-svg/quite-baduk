"""MockKataGoAdapter: deterministic GTP-compatible stand-in for tests and dev.

Plays in an 'on-demand' fashion: genmove returns the next empty intersection
scanning top-left to bottom-right. Enough for integration tests, not a real player.
"""

from __future__ import annotations

from app.core.katago.adapter import GTPResult
from app.core.katago.analysis import AnalysisResult, MoveHint
from app.core.katago.strength import StrengthConfig
from app.core.rules.board import BLACK, WHITE, Board
from app.core.rules.sgf_coord import gtp_to_xy, xy_to_gtp


class MockKataGoAdapter:
    """Drop-in replacement for KataGoAdapter."""

    def __init__(self) -> None:
        self.board_size = 19
        self.board = Board(self.board_size)
        self.komi = 6.5
        self.profile: tuple[str, int] | None = None
        self.move_history: list[tuple[str, str]] = []
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

    async def set_boardsize(self, size: int) -> None:
        self.board_size = size
        self.board = Board(size)
        self.move_history.clear()

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
            return
        xy = gtp_to_xy(coord, self.board_size)
        if xy is None:
            return
        x, y = xy
        self.board = self.board.place(x, y, color)
        self.move_history.append((color, coord))

    async def undo(self) -> None:
        if not self.move_history:
            return
        color, coord = self.move_history.pop()
        if coord.lower() == "pass":
            return
        xy = gtp_to_xy(coord, self.board_size)
        if xy is not None:
            x, y = xy
            self.board = self.board.remove(x, y)

    async def genmove(self, color: str) -> str:
        # Pick first empty intersection scanning top-left to bottom-right.
        for y in range(self.board_size):
            for x in range(self.board_size):
                if self.board.is_empty(x, y):
                    coord = xy_to_gtp(x, y, self.board_size)
                    await self.play(color, coord)
                    return coord
        return "pass"

    async def final_score(self) -> str:
        # Deterministic placeholder
        return "B+0.5"

    async def analyze(self, max_visits: int = 100) -> AnalysisResult:
        # Return 3 hints with plausible values
        hints = []
        count = 0
        for y in range(self.board_size):
            if count >= 3:
                break
            for x in range(self.board_size):
                if self.board.is_empty(x, y):
                    coord = xy_to_gtp(x, y, self.board_size)
                    hints.append(MoveHint(move=coord, visits=max_visits - count * 10, winrate=0.5 + count * 0.01))
                    count += 1
                    if count >= 3:
                        break
        return AnalysisResult(top_moves=hints, ownership=[0.0] * (self.board_size * self.board_size), winrate=0.5)

    async def version(self) -> str:
        return "Mock 1.0"

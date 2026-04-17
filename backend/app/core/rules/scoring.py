"""Korean rules territory scoring."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.rules.board import BLACK, EMPTY, WHITE, Board, BOARD_SIZE


@dataclass
class ScoreResult:
    black_territory: int
    white_territory: int
    black_captures: int
    white_captures: int
    komi: float
    black_score: float
    white_score: float
    winner: str  # 'B' or 'W'
    margin: float  # absolute difference


def _flood_territory(
    board: Board, dead_stones: set[tuple[int, int]]
) -> tuple[int, int]:
    """Flood-fill empty regions to determine territory ownership.

    An empty region belongs to BLACK if it's only adjacent to black stones,
    WHITE if only adjacent to white stones, and is neutral (dame) otherwise.

    Dead stones are treated as empty during counting.
    """
    visited: set[tuple[int, int]] = set()
    black_terr = 0
    white_terr = 0

    # Build effective board (remove dead stones)
    effective = board
    for pos in dead_stones:
        effective = effective.remove(*pos)

    def flood(sx: int, sy: int) -> tuple[set[tuple[int, int]], set[str]]:
        region: set[tuple[int, int]] = set()
        border_colors: set[str] = set()
        stack = [(sx, sy)]
        while stack:
            x, y = stack.pop()
            if (x, y) in region:
                continue
            cell = effective.get(x, y)
            if cell == EMPTY:
                region.add((x, y))
                for nx, ny in effective.neighbors(x, y):
                    if (nx, ny) not in region:
                        stack.append((nx, ny))
            else:
                border_colors.add(cell)
        return region, border_colors

    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if (x, y) not in visited and effective.get(x, y) == EMPTY:
                region, colors = flood(x, y)
                visited |= region
                if colors == {BLACK}:
                    black_terr += len(region)
                elif colors == {WHITE}:
                    white_terr += len(region)
                # neutral (dame) or seki: not counted

    return black_terr, white_terr


def score_game(
    board: Board,
    black_captures: int,
    white_captures: int,
    komi: float,
    dead_stones: set[tuple[int, int]] | None = None,
) -> ScoreResult:
    """Compute Korean-rules score.

    Korean rules: territory + captures (dead stones of opponent counted separately by caller).
    Score = territory + captures (from game) - komi (white advantage).
    """
    if dead_stones is None:
        dead_stones = set()

    # Extra captures from dead stones
    extra_black_captures = sum(
        1 for pos in dead_stones if board.get(*pos) == WHITE
    )
    extra_white_captures = sum(
        1 for pos in dead_stones if board.get(*pos) == BLACK
    )

    black_terr, white_terr = _flood_territory(board, dead_stones)

    b_score = float(black_terr + black_captures + extra_black_captures)
    w_score = white_terr + white_captures + extra_white_captures + komi

    if b_score > w_score:
        winner = BLACK
        margin = b_score - w_score
    else:
        winner = WHITE
        margin = w_score - b_score

    return ScoreResult(
        black_territory=black_terr,
        white_territory=white_terr,
        black_captures=black_captures + extra_black_captures,
        white_captures=white_captures + extra_white_captures,
        komi=komi,
        black_score=b_score,
        white_score=w_score,
        winner=winner,
        margin=margin,
    )

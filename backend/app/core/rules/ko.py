"""Ko rule: simple ko (forbid immediate recapture that recreates previous position)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.rules.board import Board


@dataclass
class KoState:
    """Tracks the previous board position to detect simple ko."""
    previous_board: Board | None = field(default=None)

    def update(self, board: Board) -> "KoState":
        return KoState(previous_board=board)


def is_ko_violation(ko_state: KoState, new_board: Board) -> bool:
    """Return True if new_board reproduces the previous position (simple ko)."""
    return ko_state.previous_board is not None and new_board == ko_state.previous_board

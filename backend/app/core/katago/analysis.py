"""Parser for `kata-analyze` GTP output.

kata-analyze streams lines like:
    info move Q16 visits 100 winrate 0.523 ... move D4 visits 50 winrate 0.497 ...

The analysis body may include many 'info move ...' segments per line,
and an 'ownership' suffix with board-size worth of floats.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MoveHint:
    move: str  # "Q16" or "pass"
    visits: int
    winrate: float  # 0.0 - 1.0
    score_lead: float = 0.0


@dataclass
class AnalysisResult:
    top_moves: list[MoveHint] = field(default_factory=list)
    ownership: list[float] = field(default_factory=list)  # length size*size
    winrate: float = 0.5  # overall winrate for side to move
    score_lead: float = 0.0  # best move's score lead from side-to-move's perspective


def parse_analysis(body: str, board_size: int = 19) -> AnalysisResult:
    """Parse kata-analyze output into structured data.

    Only the final line of the stream (last analysis snapshot) is kept.
    """
    result = AnalysisResult()
    if not body.strip():
        return result

    # Take the last non-empty 'info move ...' line
    lines = [ln for ln in body.splitlines() if ln.strip().startswith("info move")]
    if not lines:
        return result
    final_line = lines[-1]

    # Parse ownership suffix if present: 'ownership 0.12 -0.34 ...'
    ownership_idx = final_line.find("ownership")
    main = final_line[:ownership_idx] if ownership_idx >= 0 else final_line
    if ownership_idx >= 0:
        tail = final_line[ownership_idx + len("ownership"):].split()
        expected = board_size * board_size
        try:
            vals = [float(t) for t in tail[:expected]]
            if len(vals) == expected:
                result.ownership = vals
        except ValueError:
            pass

    # Split into 'info' segments
    tokens = main.split()
    segments: list[list[str]] = []
    current: list[str] = []
    for t in tokens:
        if t == "info":
            if current:
                segments.append(current)
            current = []
        else:
            current.append(t)
    if current:
        segments.append(current)

    for seg in segments:
        # seg example:
        # ['move', 'Q16', 'visits', '100', 'winrate', '0.523', 'scoreLead', '1.2', 'prior', ...]
        hint_data: dict[str, str] = {}
        i = 0
        while i < len(seg) - 1:
            hint_data[seg[i]] = seg[i + 1]
            i += 2
        try:
            move = hint_data.get("move", "")
            if not move:
                continue
            hint = MoveHint(
                move=move,
                visits=int(hint_data.get("visits", "0")),
                winrate=float(hint_data.get("winrate", "0.5")),
                score_lead=float(hint_data.get("scoreLead", "0")),
            )
            result.top_moves.append(hint)
        except (ValueError, KeyError):
            continue

    # Sort by visits desc
    result.top_moves.sort(key=lambda m: -m.visits)
    if result.top_moves:
        result.winrate = result.top_moves[0].winrate
        result.score_lead = result.top_moves[0].score_lead
    return result

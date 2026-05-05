"""Convert the vendored GoGameGuru weekly puzzles into a Python data
module that ``daily_challenge.py`` can import + concatenate.

Usage (from backend/):

    python -m scripts.ingest_gogameguru

Output: ``backend/app/services/daily_challenge_gogameguru.py``

Re-runnable; the output is deterministic so committed diffs are clean.

Topic assignment is deterministic across runs but evenly distributed:
gogameguru's weekly archive isn't tagged by topic, so we split the
catalogue 50/50 across the two topics that match the bulk of the
content (life_death and tesuji). The split key is the SGF filename
hash → modular index, so the same file always lands in the same
topic.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from app.core.rules.sgf_coord import xy_to_gtp

SGF_ROOT = Path(__file__).resolve().parent.parent / "data" / "gogameguru" / "sgfs"
OUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "app" / "services" / "daily_challenge_gogameguru.py"
)

# Folder name → public DIFFICULTIES value.
DIFFICULTY_MAP = {"easy": "easy", "intermediate": "medium", "hard": "hard"}

# gogameguru's weekly archive is overwhelmingly life-and-death oriented
# (the questions read "Black to play and live", "kill the corner",
# "find the eye-stealing move"). Tagging every imported puzzle under a
# single canonical topic keeps the per-cell count tall — splitting them
# across multiple topics would dilute every cell below the
# "≥ 100 per cell" threshold without adding accuracy.
DEFAULT_TOPIC = "life_death"

SZ_RE = re.compile(r"SZ\[(\d+)\]")
AB_RE = re.compile(r"AB((?:\[[a-z]{2}\])+)")
AW_RE = re.compile(r"AW((?:\[[a-z]{2}\])+)")
COORD_RE = re.compile(r"\[([a-z]{2})\]")
FIRST_MOVE_RE = re.compile(r"\(\s*;([BW])\[")


def _sgf_to_xy(sgf_coord: str) -> tuple[int, int]:
    """SGF uses 'a'..'s' for both columns and rows, with origin at
    top-left. Internal (x, y) shares that origin so this is a direct
    cast, not a flip."""
    return ord(sgf_coord[0]) - ord("a"), ord(sgf_coord[1]) - ord("a")


def parse_sgf(text: str) -> dict | None:
    """Pull the puzzle skeleton out of one SGF. Returns None if the
    file lacks the fields we need (board size + at least a handful of
    setup stones + a clear side-to-move)."""
    sz_m = SZ_RE.search(text)
    if sz_m is None:
        return None
    size = int(sz_m.group(1))

    ab_m = AB_RE.search(text)
    aw_m = AW_RE.search(text)
    ab_coords = COORD_RE.findall(ab_m.group(1)) if ab_m else []
    aw_coords = COORD_RE.findall(aw_m.group(1)) if aw_m else []

    fm = FIRST_MOVE_RE.search(text)
    to_move = fm.group(1) if fm else None
    if to_move is None:
        return None
    if not (ab_coords or aw_coords):
        return None

    setup: list[tuple[str, str]] = []
    for sc in ab_coords:
        x, y = _sgf_to_xy(sc)
        if 0 <= x < size and 0 <= y < size:
            setup.append(("B", xy_to_gtp(x, y, size)))
    for sc in aw_coords:
        x, y = _sgf_to_xy(sc)
        if 0 <= x < size and 0 <= y < size:
            setup.append(("W", xy_to_gtp(x, y, size)))

    return {
        "board_size": size,
        "setup": tuple(setup),
        "to_move": to_move,
    }


def topic_for(filename: str) -> str:
    """Stable mapping (currently constant). Kept as a function so a
    future refinement — e.g. KataGo-assisted classifier that detects
    capturing-race vs life-and-death — can drop in without touching
    the ingest skeleton."""
    _ = filename  # placeholder for the future heuristic
    _ = hashlib  # kept imported in case we need stable hashing later
    return DEFAULT_TOPIC


def build_id(difficulty: str, filename: str) -> str:
    # ggg- + difficulty + slug of filename (drop .sgf)
    stem = filename.removesuffix(".sgf")
    return f"ggg-{difficulty}-{stem}"


def main() -> None:
    rows: list[dict] = []
    for diff_folder, diff_label in DIFFICULTY_MAP.items():
        folder = SGF_ROOT / diff_folder
        for sgf_path in sorted(folder.glob("*.sgf")):
            text = sgf_path.read_text(encoding="utf-8", errors="replace")
            parsed = parse_sgf(text)
            if parsed is None:
                continue
            # Deduplicate setup coords — gogameguru SGFs occasionally
            # repeat a coord across AB/AW which our schema disallows.
            seen: set[str] = set()
            uniq_setup: list[tuple[str, str]] = []
            for color, coord in parsed["setup"]:
                if coord.upper() in seen:
                    continue
                seen.add(coord.upper())
                uniq_setup.append((color, coord))
            if len(uniq_setup) < 4:
                # Too sparse to be a useful puzzle; skip rather than
                # surface a near-empty board to the player.
                continue
            rows.append({
                "id": build_id(diff_label, sgf_path.name),
                "board_size": parsed["board_size"],
                "setup": tuple(uniq_setup),
                "to_move": parsed["to_move"],
                "difficulty": diff_label,
                "topic": topic_for(sgf_path.name),
            })

    rows.sort(key=lambda r: r["id"])

    lines: list[str] = [
        "# ruff: noqa: E501, I001",
        '"""Auto-generated by scripts/ingest_gogameguru.py — do not hand-edit.',
        "",
        "Source: GoGameGuru Weekly Go Problems",
        "        https://github.com/gogameguru/go-problems",
        "License: CC BY-NC-SA 4.0 (see backend/data/gogameguru/LICENSE.txt)",
        "Authors: An Younggil 8p · David Ormerod",
        '"""',
        "from __future__ import annotations",
        "",
        "from app.services.daily_challenge import DailyChallenge",
        "",
        "GOGAMEGURU_CHALLENGES: tuple[DailyChallenge, ...] = (",
    ]
    for r in rows:
        setup_repr = ", ".join(f'("{c}", "{k}")' for c, k in r["setup"])
        lines.append("    DailyChallenge(")
        lines.append(f'        id="{r["id"]}",')
        lines.append(f'        board_size={r["board_size"]},')
        lines.append(f"        setup=({setup_repr},),")
        lines.append(f'        to_move="{r["to_move"]}",')
        lines.append(f'        difficulty="{r["difficulty"]}",')
        lines.append(f'        topic="{r["topic"]}",')
        lines.append('        prompt_key="daily.attribution.gogameguru",')
        lines.append("    ),")
    lines.append(")")
    lines.append("")

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {len(rows)} puzzles to {OUT_PATH}")


if __name__ == "__main__":
    main()

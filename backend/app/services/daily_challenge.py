"""Baduk puzzle catalogue.

Each puzzle is a (color, coord) play sequence so the rules engine can
rebuild the board deterministically. Puzzles carry a topic + difficulty
+ board size; KataGo grades the user's answer at request time.

Topic taxonomy (V1 launch): the seven traditional Asian go-textbook
chapters — opening / joseki / life_death / tesuji / middle_game /
endgame / capturing_race. Frontend mirrors these strings.
"""
from __future__ import annotations

import datetime as _dt
import random
from dataclasses import dataclass

from app.core.rules.board import BLACK, WHITE, Board
from app.core.rules.engine import GameState
from app.core.rules.sgf_coord import gtp_to_xy, xy_to_gtp

TOPICS: tuple[str, ...] = (
    "opening",
    "joseki",
    "life_death",
    "tesuji",
    "middle_game",
    "endgame",
    "capturing_race",
)
DIFFICULTIES: tuple[str, ...] = ("easy", "medium", "hard")
BOARD_SIZES: tuple[int, ...] = (9, 13, 19)


@dataclass(frozen=True)
class DailyChallenge:
    id: str
    board_size: int
    setup: tuple[tuple[str, str], ...]
    to_move: str         # "B" or "W"
    difficulty: str      # "easy" | "medium" | "hard"
    topic: str           # one of TOPICS
    prompt_key: str      # i18n key — frontend resolves to a description


def _ch(
    id: str,
    *,
    size: int,
    setup: tuple[tuple[str, str], ...],
    to_move: str,
    difficulty: str,
    topic: str,
) -> DailyChallenge:
    """Builder. Most new puzzles share a topic-level prompt — the per-id
    prompt key is reserved for entries that need bespoke flavour text."""
    return DailyChallenge(
        id=id,
        board_size=size,
        setup=setup,
        to_move=to_move,
        difficulty=difficulty,
        topic=topic,
        prompt_key=f"daily.topicPrompt.{topic}",
    )


# V1 catalogue. Hand-authored to populate every (size × topic) combo at
# at least one difficulty so the filter UI doesn't dead-end. KataGo
# grades, so positions only need to be coherent — not literature.
CHALLENGES: tuple[DailyChallenge, ...] = (
    # ── 9×9 opening ───────────────────────────────────────────────────
    _ch("ch-9-op-1", size=9, to_move="W", difficulty="easy", topic="opening",
        setup=(("B", "E5"), ("W", "C3"), ("B", "G7"), ("W", "G3"), ("B", "C7"))),
    _ch("ch-9-op-2", size=9, to_move="W", difficulty="medium", topic="opening",
        setup=(("B", "E5"), ("W", "C5"), ("B", "G5"), ("W", "C3"),
               ("B", "G3"), ("W", "C7"), ("B", "G7"))),
    _ch("ch-9-op-3", size=9, to_move="B", difficulty="hard", topic="opening",
        setup=(("B", "C3"), ("W", "G7"), ("B", "G3"), ("W", "C7"))),
    # ── 9×9 joseki ────────────────────────────────────────────────────
    _ch("ch-9-jo-1", size=9, to_move="W", difficulty="easy", topic="joseki",
        setup=(("B", "C3"), ("W", "C5"), ("B", "E3"))),
    _ch("ch-9-jo-2", size=9, to_move="B", difficulty="medium", topic="joseki",
        setup=(("B", "C7"), ("W", "C5"), ("B", "E7"), ("W", "C8"))),
    _ch("ch-9-jo-3", size=9, to_move="W", difficulty="hard", topic="joseki",
        setup=(("B", "G3"), ("W", "G5"), ("B", "E3"), ("W", "G7"), ("B", "F5"))),
    # ── 9×9 life_death ────────────────────────────────────────────────
    _ch("ch-9-ld-1", size=9, to_move="B", difficulty="easy", topic="life_death",
        setup=(("B", "B7"), ("B", "B8"), ("B", "C7"), ("W", "D7"),
               ("W", "D8"), ("W", "C6"), ("W", "B6"))),
    _ch("ch-9-ld-2", size=9, to_move="B", difficulty="medium", topic="life_death",
        setup=(("B", "C7"), ("W", "D7"), ("B", "C8"), ("W", "D8"),
               ("B", "C6"), ("W", "D6"), ("B", "B7"), ("W", "E7"))),
    _ch("ch-9-ld-3", size=9, to_move="W", difficulty="hard", topic="life_death",
        setup=(("B", "B2"), ("B", "C2"), ("B", "D2"), ("B", "B3"),
               ("W", "C3"), ("W", "D3"), ("W", "B4"), ("W", "E2"))),
    # ── 9×9 tesuji ────────────────────────────────────────────────────
    _ch("ch-9-te-1", size=9, to_move="B", difficulty="easy", topic="tesuji",
        setup=(("B", "D5"), ("W", "E5"), ("B", "E4"), ("W", "D4"))),
    _ch("ch-9-te-2", size=9, to_move="W", difficulty="medium", topic="tesuji",
        setup=(("B", "C5"), ("W", "D5"), ("B", "D6"), ("W", "E6"),
               ("B", "C6"), ("W", "E5"))),
    _ch("ch-9-te-3", size=9, to_move="B", difficulty="hard", topic="tesuji",
        setup=(("B", "F4"), ("W", "F5"), ("B", "G5"), ("W", "G6"),
               ("B", "F6"), ("W", "G4"), ("B", "E5"))),
    # ── 9×9 middle_game ───────────────────────────────────────────────
    _ch("ch-9-mg-1", size=9, to_move="B", difficulty="easy", topic="middle_game",
        setup=(("B", "E5"), ("W", "G5"), ("B", "C5"), ("W", "E7"),
               ("B", "E3"))),
    _ch("ch-9-mg-2", size=9, to_move="B", difficulty="medium", topic="middle_game",
        setup=(("B", "E5"), ("W", "G5"), ("B", "E7"), ("W", "G7"),
               ("B", "E3"), ("W", "G3"))),
    _ch("ch-9-mg-3", size=9, to_move="B", difficulty="hard", topic="middle_game",
        setup=(("B", "C5"), ("W", "G5"), ("B", "E3"), ("W", "E7"),
               ("B", "G7"), ("W", "C3"), ("B", "G3"), ("W", "C7"))),
    # ── 9×9 endgame ───────────────────────────────────────────────────
    _ch("ch-9-en-1", size=9, to_move="W", difficulty="easy", topic="endgame",
        setup=(("B", "E5"), ("W", "C3"), ("B", "G7"), ("W", "G3"),
               ("B", "C7"), ("W", "E3"), ("B", "C5"), ("W", "G5"),
               ("B", "E7"), ("W", "D2"), ("B", "F8"))),
    _ch("ch-9-en-2", size=9, to_move="B", difficulty="medium", topic="endgame",
        setup=(("B", "C3"), ("W", "G3"), ("B", "C7"), ("W", "G7"),
               ("B", "E5"), ("W", "E3"), ("B", "E7"), ("W", "B5"),
               ("B", "C5"), ("W", "H5"), ("B", "G5"), ("W", "F2"))),
    _ch("ch-9-en-3", size=9, to_move="W", difficulty="hard", topic="endgame",
        setup=(("B", "C3"), ("W", "G3"), ("B", "C7"), ("W", "G7"),
               ("B", "E5"), ("W", "B5"), ("B", "C5"), ("W", "H5"),
               ("B", "G5"), ("W", "E3"), ("B", "E7"), ("W", "F2"),
               ("B", "B3"))),
    # ── 9×9 capturing_race ────────────────────────────────────────────
    _ch("ch-9-cr-1", size=9, to_move="B", difficulty="easy", topic="capturing_race",
        setup=(("B", "B5"), ("B", "C5"), ("B", "D5"), ("W", "B6"),
               ("W", "C6"), ("W", "D6"), ("B", "E5"), ("W", "E6"))),
    _ch("ch-9-cr-2", size=9, to_move="W", difficulty="medium", topic="capturing_race",
        setup=(("B", "C2"), ("B", "C3"), ("B", "C4"), ("W", "D2"),
               ("W", "D3"), ("W", "D4"), ("B", "B3"), ("W", "E3"))),
    _ch("ch-9-cr-3", size=9, to_move="B", difficulty="hard", topic="capturing_race",
        setup=(("B", "G2"), ("B", "G3"), ("B", "G4"), ("W", "H2"),
               ("W", "H3"), ("W", "H4"), ("B", "F3"), ("W", "G5"),
               ("B", "F4"))),

    # ── 13×13 opening ─────────────────────────────────────────────────
    _ch("ch-13-op-1", size=13, to_move="B", difficulty="easy", topic="opening",
        setup=(("B", "D4"), ("W", "K10"), ("B", "K4"), ("W", "D10"))),
    _ch("ch-13-op-2", size=13, to_move="W", difficulty="medium", topic="opening",
        setup=(("B", "D4"), ("W", "K10"), ("B", "K4"), ("W", "D10"),
               ("B", "G7"))),
    _ch("ch-13-op-3", size=13, to_move="B", difficulty="hard", topic="opening",
        setup=(("B", "D4"), ("W", "K10"), ("B", "K4"), ("W", "D10"),
               ("B", "G7"), ("W", "G4"), ("B", "G10"), ("W", "K7"))),
    # ── 13×13 joseki ──────────────────────────────────────────────────
    _ch("ch-13-jo-1", size=13, to_move="W", difficulty="easy", topic="joseki",
        setup=(("B", "D4"), ("W", "F4"), ("B", "D6"))),
    _ch("ch-13-jo-2", size=13, to_move="B", difficulty="medium", topic="joseki",
        setup=(("B", "K4"), ("W", "K6"), ("B", "H4"), ("W", "K7"))),
    _ch("ch-13-jo-3", size=13, to_move="W", difficulty="hard", topic="joseki",
        setup=(("B", "K10"), ("W", "K12"), ("B", "J12"), ("W", "K11"),
               ("B", "L11"), ("W", "L12"))),
    # ── 13×13 life_death ──────────────────────────────────────────────
    _ch("ch-13-ld-1", size=13, to_move="B", difficulty="easy", topic="life_death",
        setup=(("B", "B11"), ("B", "C11"), ("B", "C12"), ("W", "D11"),
               ("W", "D12"), ("W", "B12"), ("W", "B10"))),
    _ch("ch-13-ld-2", size=13, to_move="W", difficulty="medium", topic="life_death",
        setup=(("B", "L2"), ("B", "L3"), ("B", "L4"), ("B", "K4"),
               ("W", "M3"), ("W", "M4"), ("W", "K3"))),
    _ch("ch-13-ld-3", size=13, to_move="B", difficulty="hard", topic="life_death",
        setup=(("B", "B2"), ("B", "C2"), ("B", "D2"), ("B", "B3"),
               ("W", "C3"), ("W", "D3"), ("W", "B4"), ("W", "E2"),
               ("W", "E3"))),
    # ── 13×13 tesuji ──────────────────────────────────────────────────
    _ch("ch-13-te-1", size=13, to_move="B", difficulty="easy", topic="tesuji",
        setup=(("B", "G7"), ("W", "G8"), ("B", "H8"), ("W", "H7"))),
    _ch("ch-13-te-2", size=13, to_move="W", difficulty="medium", topic="tesuji",
        setup=(("B", "F6"), ("W", "G6"), ("B", "G7"), ("W", "H7"),
               ("B", "F7"), ("W", "H6"))),
    _ch("ch-13-te-3", size=13, to_move="B", difficulty="hard", topic="tesuji",
        setup=(("B", "F4"), ("W", "F5"), ("B", "G5"), ("W", "G6"),
               ("B", "F6"), ("W", "G4"), ("B", "E5"))),
    # ── 13×13 middle_game ─────────────────────────────────────────────
    _ch("ch-13-mg-1", size=13, to_move="W", difficulty="easy", topic="middle_game",
        setup=(("B", "D4"), ("W", "K10"), ("B", "K4"), ("W", "D10"),
               ("B", "G7"))),
    _ch("ch-13-mg-2", size=13, to_move="W", difficulty="medium", topic="middle_game",
        setup=(("B", "D4"), ("W", "K10"), ("B", "K4"), ("W", "D10"),
               ("B", "G7"), ("W", "G4"), ("B", "G10"))),
    _ch("ch-13-mg-3", size=13, to_move="B", difficulty="hard", topic="middle_game",
        setup=(("B", "D4"), ("W", "K10"), ("B", "K4"), ("W", "D10"),
               ("B", "D7"), ("W", "K7"), ("B", "G3"), ("W", "G11"))),
    # ── 13×13 endgame ─────────────────────────────────────────────────
    _ch("ch-13-en-0", size=13, to_move="B", difficulty="easy", topic="endgame",
        setup=(("B", "D4"), ("W", "K10"), ("B", "K4"), ("W", "D10"),
               ("B", "G7"), ("W", "G4"), ("B", "G10"))),
    _ch("ch-13-en-1", size=13, to_move="W", difficulty="medium", topic="endgame",
        setup=(("B", "D4"), ("W", "K10"), ("B", "K4"), ("W", "D10"),
               ("B", "G7"), ("W", "G4"), ("B", "G10"), ("W", "K7"),
               ("B", "D7"), ("W", "D11"), ("B", "C9"))),
    _ch("ch-13-en-2", size=13, to_move="B", difficulty="hard", topic="endgame",
        setup=(("B", "D4"), ("W", "K10"), ("B", "K4"), ("W", "D10"),
               ("B", "G7"), ("W", "G4"), ("B", "G10"), ("W", "K7"),
               ("B", "D7"), ("W", "D11"), ("B", "C9"), ("W", "L11"),
               ("B", "L4"), ("W", "M10"))),
    # ── 13×13 capturing_race ──────────────────────────────────────────
    _ch("ch-13-cr-0", size=13, to_move="W", difficulty="easy", topic="capturing_race",
        setup=(("B", "B6"), ("B", "C6"), ("B", "D6"), ("W", "B7"),
               ("W", "C7"), ("W", "D7"), ("B", "E6"), ("W", "E7"))),
    _ch("ch-13-cr-1", size=13, to_move="B", difficulty="medium", topic="capturing_race",
        setup=(("B", "C2"), ("B", "D2"), ("B", "E2"), ("W", "C3"),
               ("W", "D3"), ("W", "E3"), ("B", "F2"), ("W", "B3"))),
    _ch("ch-13-cr-2", size=13, to_move="B", difficulty="hard", topic="capturing_race",
        setup=(("B", "K2"), ("B", "L2"), ("B", "M2"), ("W", "K3"),
               ("W", "L3"), ("W", "M3"), ("B", "J2"), ("W", "J3"),
               ("B", "K4"))),

    # ── 19×19 opening ─────────────────────────────────────────────────
    _ch("ch-19-op-1", size=19, to_move="B", difficulty="easy", topic="opening",
        setup=(("B", "Q16"), ("W", "D4"), ("B", "D16"), ("W", "Q4"))),
    _ch("ch-19-op-2", size=19, to_move="W", difficulty="medium", topic="opening",
        setup=(("B", "Q16"), ("W", "D4"), ("B", "D16"), ("W", "Q4"),
               ("B", "K10"))),
    _ch("ch-19-op-3", size=19, to_move="B", difficulty="hard", topic="opening",
        setup=(("B", "Q16"), ("W", "D4"), ("B", "D16"), ("W", "Q4"),
               ("B", "Q10"), ("W", "C10"))),
    # ── 19×19 joseki ──────────────────────────────────────────────────
    _ch("ch-19-jo-1", size=19, to_move="W", difficulty="easy", topic="joseki",
        setup=(("B", "Q16"), ("W", "Q14"), ("B", "P14"))),
    _ch("ch-19-jo-2", size=19, to_move="B", difficulty="medium", topic="joseki",
        setup=(("B", "D16"), ("W", "F17"), ("B", "F16"), ("W", "G16"),
               ("B", "F15"))),
    _ch("ch-19-jo-3", size=19, to_move="W", difficulty="hard", topic="joseki",
        setup=(("B", "Q16"), ("W", "Q14"), ("B", "P14"), ("W", "P13"),
               ("B", "O14"), ("W", "Q13"), ("B", "P15"))),
    # ── 19×19 life_death ──────────────────────────────────────────────
    _ch("ch-19-ld-0", size=19, to_move="B", difficulty="easy", topic="life_death",
        setup=(("B", "C17"), ("B", "D17"), ("B", "D18"), ("W", "E17"),
               ("W", "E18"), ("W", "C18"), ("W", "B17"))),
    _ch("ch-19-ld-1", size=19, to_move="B", difficulty="medium", topic="life_death",
        setup=(("B", "B17"), ("B", "C17"), ("B", "C18"), ("W", "D18"),
               ("W", "D17"), ("W", "B18"), ("W", "B16"))),
    _ch("ch-19-ld-2", size=19, to_move="W", difficulty="hard", topic="life_death",
        setup=(("B", "B2"), ("B", "C2"), ("B", "D2"), ("B", "B3"),
               ("W", "C3"), ("W", "D3"), ("W", "B4"), ("W", "E2"),
               ("W", "E3"))),
    # ── 19×19 tesuji ──────────────────────────────────────────────────
    _ch("ch-19-te-0", size=19, to_move="B", difficulty="easy", topic="tesuji",
        setup=(("B", "K8"), ("W", "K9"), ("B", "L9"), ("W", "L8"))),
    _ch("ch-19-te-1", size=19, to_move="B", difficulty="medium", topic="tesuji",
        setup=(("B", "K10"), ("W", "K11"), ("B", "L11"), ("W", "L10"))),
    _ch("ch-19-te-2", size=19, to_move="W", difficulty="hard", topic="tesuji",
        setup=(("B", "K10"), ("W", "L10"), ("B", "L11"), ("W", "M11"),
               ("B", "K11"), ("W", "M10"))),
    # ── 19×19 middle_game ─────────────────────────────────────────────
    _ch("ch-19-mg-0", size=19, to_move="B", difficulty="easy", topic="middle_game",
        setup=(("B", "Q16"), ("W", "D4"), ("B", "D16"), ("W", "Q4"),
               ("B", "K10"))),
    _ch("ch-19-mg-1", size=19, to_move="W", difficulty="medium", topic="middle_game",
        setup=(("B", "Q16"), ("W", "D4"), ("B", "D16"), ("W", "Q4"),
               ("B", "Q10"), ("W", "C10"), ("B", "K3"))),
    _ch("ch-19-mg-2", size=19, to_move="B", difficulty="hard", topic="middle_game",
        setup=(("B", "Q16"), ("W", "D4"), ("B", "D16"), ("W", "Q4"),
               ("B", "Q10"), ("W", "C10"), ("B", "K3"), ("W", "K17"))),
    # ── 19×19 endgame ─────────────────────────────────────────────────
    _ch("ch-19-en-0", size=19, to_move="W", difficulty="easy", topic="endgame",
        setup=(("B", "Q16"), ("W", "D4"), ("B", "D16"), ("W", "Q4"),
               ("B", "Q10"), ("W", "D10"))),
    _ch("ch-19-en-m", size=19, to_move="B", difficulty="medium", topic="endgame",
        setup=(("B", "Q16"), ("W", "D4"), ("B", "D16"), ("W", "Q4"),
               ("B", "Q10"), ("W", "C10"), ("B", "K3"), ("W", "K17"),
               ("B", "F3"))),
    _ch("ch-19-en-1", size=19, to_move="W", difficulty="hard", topic="endgame",
        setup=(("B", "Q16"), ("W", "D4"), ("B", "D16"), ("W", "Q4"),
               ("B", "Q10"), ("W", "C10"), ("B", "K3"), ("W", "K17"),
               ("B", "F3"), ("W", "C6"), ("B", "Q6"), ("W", "Q12"),
               ("B", "P12"))),
    # ── 19×19 capturing_race ──────────────────────────────────────────
    _ch("ch-19-cr-0", size=19, to_move="W", difficulty="easy", topic="capturing_race",
        setup=(("B", "B6"), ("B", "C6"), ("B", "D6"), ("W", "B7"),
               ("W", "C7"), ("W", "D7"), ("B", "E6"), ("W", "E7"))),
    _ch("ch-19-cr-1", size=19, to_move="B", difficulty="medium", topic="capturing_race",
        setup=(("B", "B3"), ("B", "C3"), ("B", "D3"), ("W", "B4"),
               ("W", "C4"), ("W", "D4"), ("B", "E3"), ("W", "B2"))),
    _ch("ch-19-cr-2", size=19, to_move="B", difficulty="hard", topic="capturing_race",
        setup=(("B", "Q2"), ("B", "R2"), ("B", "S2"), ("W", "Q3"),
               ("W", "R3"), ("W", "S3"), ("B", "P2"), ("W", "P3"),
               ("B", "Q4"))),
)

def _attach_imports() -> tuple[DailyChallenge, ...]:
    """Late-bind imported catalogues so the data files can reference
    DailyChallenge from this module without a circular import."""
    try:
        from app.services.daily_challenge_gogameguru import (
            GOGAMEGURU_CHALLENGES,
        )
    except ImportError:
        return ()
    return GOGAMEGURU_CHALLENGES


# Public catalogue = hand-curated core + every imported set. Variants
# are applied at pick time via D4 transforms; this tuple is the raw
# base set.
CHALLENGES = CHALLENGES + _attach_imports()


_BY_ID: dict[str, DailyChallenge] = {c.id: c for c in CHALLENGES}


# ─── Geometric variants (D4 dihedral group) ───────────────────────────
#
# A Go board has the symmetry group of a square: 4 rotations × {id,
# reflection} = 8 orientations. Two stones in geometrically equivalent
# positions play the same go even though the move list looks different.
# We exploit this to multiply the catalogue by ~8 without composing
# new positions: every puzzle id can carry an optional ".t<idx>" suffix
# (idx 0..7) which the resolver applies as a coordinate transform.

NUM_VARIANTS = 8


def _transform_xy(x: int, y: int, size: int, t: int) -> tuple[int, int]:
    n = size - 1
    # Eight elements of the dihedral group D4 over the board grid.
    if t == 0:
        return x, y                       # identity
    if t == 1:
        return n - y, x                   # rot 90 ccw
    if t == 2:
        return n - x, n - y               # rot 180
    if t == 3:
        return y, n - x                   # rot 270 ccw
    if t == 4:
        return n - x, y                   # flip across vertical axis
    if t == 5:
        return x, n - y                   # flip across horizontal axis
    if t == 6:
        return y, x                       # transpose (main diagonal)
    if t == 7:
        return n - y, n - x               # anti-transpose
    raise ValueError(f"transform idx must be 0..7, got {t}")


def _transform_coord(coord: str, size: int, t: int) -> str:
    xy = gtp_to_xy(coord, size)
    if xy is None:
        return coord
    nx, ny = _transform_xy(xy[0], xy[1], size, t)
    return xy_to_gtp(nx, ny, size)


def _apply_transform(base: DailyChallenge, t: int) -> DailyChallenge:
    """Return a new DailyChallenge whose setup is the geometrically
    transformed version of ``base``. Identity transform returns the
    base unchanged. The id gains a ``.t<idx>`` suffix so the answer
    endpoint can recover both pieces."""
    if t == 0:
        return base
    new_setup = tuple(
        (color, _transform_coord(coord, base.board_size, t))
        for color, coord in base.setup
    )
    return DailyChallenge(
        id=f"{base.id}.t{t}",
        board_size=base.board_size,
        setup=new_setup,
        to_move=base.to_move,
        difficulty=base.difficulty,
        topic=base.topic,
        prompt_key=base.prompt_key,
    )


def _split_id(challenge_id: str) -> tuple[str, int]:
    """Parse a maybe-transformed id into (base_id, transform_idx).
    Untransformed ids return transform 0."""
    if ".t" not in challenge_id:
        return challenge_id, 0
    base, _, suffix = challenge_id.rpartition(".t")
    try:
        t = int(suffix)
    except ValueError:
        return challenge_id, 0
    if not 0 <= t < NUM_VARIANTS:
        return challenge_id, 0
    return base, t


def daily_index(today: _dt.date | None = None) -> int:
    today = today or _dt.date.today()
    epoch = _dt.date(1970, 1, 1)
    return (today.toordinal() - epoch.toordinal()) % len(CHALLENGES)


def get_today(today: _dt.date | None = None) -> DailyChallenge:
    return CHALLENGES[daily_index(today)]


def get_by_id(challenge_id: str) -> DailyChallenge | None:
    """Resolve a (possibly transformed) id back to a concrete puzzle.
    The grader uses this to reconstruct the exact position the user
    saw — without it the user's answer would land on the un-rotated
    variant and KataGo would grade against the wrong board."""
    base_id, t = _split_id(challenge_id)
    base = _BY_ID.get(base_id)
    if base is None:
        return None
    return _apply_transform(base, t)


def filter_challenges(
    *,
    board_size: int | None = None,
    difficulty: str | None = None,
    topic: str | None = None,
) -> tuple[DailyChallenge, ...]:
    return tuple(
        c for c in CHALLENGES
        if (board_size is None or c.board_size == board_size)
        and (difficulty is None or c.difficulty == difficulty)
        and (topic is None or c.topic == topic)
    )


def pick_random(
    *,
    board_size: int | None = None,
    difficulty: str | None = None,
    topic: str | None = None,
    exclude_id: str | None = None,
    rng: random.Random | None = None,
) -> DailyChallenge | None:
    """Random pick within filters, with a random D4 transform applied
    so the player sees a fresh-looking position even when the same base
    is reused.

    Two layers of "different from last time":
      1. Prefer a different *base* puzzle when one exists in the filter.
      2. Otherwise fall back to the same base with a different transform
         (the user gets a rotated / mirrored version of the puzzle they
         just solved — visually fresh, semantically the same).

    Returns ``None`` only when the filter has zero base puzzles AND the
    excluded base was the only one (i.e. literally nothing else to ship)."""
    # Puzzle pick is non-cryptographic — Random() is appropriate here.
    r: random.Random = rng if rng is not None else random.Random()  # noqa: S311
    matches = filter_challenges(
        board_size=board_size, difficulty=difficulty, topic=topic
    )
    if not matches:
        return None

    excluded_base, excluded_t = (
        _split_id(exclude_id) if exclude_id else (None, 0)
    )

    # Layer 1: prefer a different base.
    other_bases = (
        tuple(c for c in matches if c.id != excluded_base)
        if excluded_base
        else matches
    )
    if other_bases:
        base = r.choice(other_bases)
        t = r.randrange(NUM_VARIANTS)
        return _apply_transform(base, t)

    # Layer 2: same base, different transform.
    if excluded_base:
        same = tuple(c for c in matches if c.id == excluded_base)
        if same:
            base = same[0]
            other_ts = [t for t in range(NUM_VARIANTS) if t != excluded_t]
            t = r.choice(other_ts)
            return _apply_transform(base, t)

    return None


def replay_position(challenge: DailyChallenge) -> GameState:
    """Build the puzzle position by directly placing each setup stone.

    We *don't* route through the rules engine's ``play()`` here because
    puzzle setups frequently break strict turn alternation — life-and-
    death and capturing-race positions naturally have several Black
    stones in a row, then several White, etc. ``play()`` would refuse
    them with NOT_YOUR_TURN. The setup describes a final position, not
    a game; direct ``board.place()`` is the right primitive.

    Captures aren't applied during placement either — V1 catalogue
    positions are settled (every stone has a liberty), so this is a
    no-op in practice. If a future puzzle relies on a setup that ought
    to capture, switch to ``apply_captures(board, x, y, color)``.
    """
    board = Board(challenge.board_size)
    for color, coord in challenge.setup:
        c = BLACK if color == "B" else WHITE
        xy = gtp_to_xy(coord, board.size)
        if xy is None:
            raise ValueError(f"daily challenge {challenge.id}: bad coord {coord!r}")
        x, y = xy
        board = board.place(x, y, c)
    return GameState(
        board=board,
        komi=6.5,
        to_move=BLACK if challenge.to_move == "B" else WHITE,
    )

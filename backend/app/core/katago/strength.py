"""Maps UI rank (+ style/player) strings to KataGo humanSLProfile + maxVisits.

The Human-SL model (b18c384nbt-humanv0) simulates real human play at each rank.
`maxVisits` adds tree search on top; higher = stronger.

Resolution rules (rank is always honored):
  * Rank dictates the profile's rank slot — every resolved profile is
    ``rank_{rank}`` or ``preaz_{rank}``; never a fixed ``proyear_YEAR`` that
    would override the user's chosen strength.
  * Style selects the profile *family* (modern ``rank_`` vs pre-AZ ``preaz_``)
    and a visit-count multiplier.
  * A known player inherits its style category (which in turn picks the
    family + visits multiplier); the player's proyear is intentionally not
    used for the profile string, since KataGo cannot combine a fixed pro-year
    with an amateur rank.
  * Unknown style/player silently fall back to ``balanced``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.katago.players import get_player
from app.core.katago.style import DEFAULT_STYLE, resolve_human_sl_profile, style_to_profile


class UnsupportedRank(ValueError):
    """Raised when a caller asks for a rank not in the public v1.0 set."""


@dataclass(frozen=True)
class StrengthConfig:
    rank: str
    human_sl_profile: str
    max_visits: int


# Baseline visit budgets per rank, tuned for the default 'balanced' style.
# Style multipliers (see app.core.katago.style) scale these up or down.
# The exponential ladder roughly doubles visits every couple of ranks, so
# playing strength tracks rank perception instead of saturating at the low
# end. v1.0 caps the public picker at 5d / 256 visits — entries above that
# (6d–9d) are kept in the table for the style/profile resolution helpers
# that exhaustively iterate `SUPPORTED_RANKS`, but they're gated out of the
# public surface by `SUPPORTED_AI_RANKS` below.
_RANK_BASE_VISITS: dict[str, int] = {
    "18k": 1,
    "15k": 1,
    "12k": 1,
    "10k": 2,
    "9k":  2,
    "8k":  3,
    "7k":  4,
    "6k":  6,
    "5k":  8,
    "4k":  12,
    "3k":  16,
    "2k":  24,
    "1k":  32,
    "1d":  64,
    "2d":  96,
    "3d":  128,
    "4d":  192,
    "5d":  256,
    "6d":  384,
    "7d":  512,
    "8d":  768,
    "9d":  1024,
}

SUPPORTED_RANKS: tuple[str, ...] = tuple(_RANK_BASE_VISITS.keys())

# Public v1.0 launch set — the rank picker exposes 9-kyu through 9-dan.
# 18k..10k are excluded as too-easy floor; 6d..9d are kept in the public
# set with the standard 256-visit cap (see ``rank_to_config`` below). The
# strength signal at the high-dan steps comes from the humanSL profile
# (``rank_9d`` vs ``rank_6d``), since visits saturate at the cap. Every
# entry here must have ``max_visits <= 256`` once style multipliers settle.
SUPPORTED_AI_RANKS: tuple[str, ...] = (
    "9k", "8k", "7k", "6k", "5k", "4k", "3k", "2k", "1k",
    "1d", "2d", "3d", "4d", "5d", "6d", "7d", "8d", "9d",
)


def rank_to_config(
    rank: str,
    style: str = DEFAULT_STYLE,
    player: str | None = None,
) -> StrengthConfig:
    """Look up strength config for rank + style + optional player.

    Rank is the primary signal — the resolved profile always carries the
    chosen rank so KataGo's move prior matches what the user asked for. A
    known ``player`` contributes its style category (which selects the
    profile family and the visit-count multiplier) but never overrides the
    rank. Unknown style/player values silently fall back to ``balanced``.

    Raises :class:`UnsupportedRank` if the rank is outside the public v1.0
    set (``SUPPORTED_AI_RANKS``).
    """
    if rank not in SUPPORTED_AI_RANKS:
        raise UnsupportedRank(rank)
    if rank not in _RANK_BASE_VISITS:
        # Defensive: keep the legacy KeyError contract for ranks that are in
        # the public set but somehow missing from the visit table.
        raise KeyError(f"Unsupported rank: {rank!r}. Supported: {SUPPORTED_RANKS}")
    base_visits = _RANK_BASE_VISITS[rank]

    p = get_player(player)
    effective_style = p.style if p is not None else style
    prof = style_to_profile(effective_style, rank)
    human_sl_profile = resolve_human_sl_profile(effective_style, rank)

    visits = max(1, min(256, int(round(base_visits * prof.visits_multiplier))))
    return StrengthConfig(
        rank=rank,
        human_sl_profile=human_sl_profile,
        max_visits=visits,
    )

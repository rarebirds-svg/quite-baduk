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


@dataclass(frozen=True)
class StrengthConfig:
    rank: str
    human_sl_profile: str
    max_visits: int


# Baseline visit budgets per rank, tuned for the default 'balanced' style.
# Style multipliers (see app.core.katago.style) scale these up or down.
_RANK_BASE_VISITS: dict[str, int] = {
    "18k": 1,
    "15k": 1,
    "12k": 1,
    "10k": 2,
    "7k":  4,
    "5k":  8,
    "3k":  16,
    "1k":  32,
    "1d":  64,
    "3d":  128,
    "5d":  256,
    "7d":  512,
}

SUPPORTED_RANKS: tuple[str, ...] = tuple(_RANK_BASE_VISITS.keys())


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

    Raises ``KeyError`` if the rank is unknown.
    """
    if rank not in _RANK_BASE_VISITS:
        raise KeyError(f"Unsupported rank: {rank!r}. Supported: {SUPPORTED_RANKS}")
    base_visits = _RANK_BASE_VISITS[rank]

    p = get_player(player)
    effective_style = p.style if p is not None else style
    prof = style_to_profile(effective_style, rank)
    human_sl_profile = resolve_human_sl_profile(effective_style, rank)

    visits = max(1, int(round(base_visits * prof.visits_multiplier)))
    return StrengthConfig(
        rank=rank,
        human_sl_profile=human_sl_profile,
        max_visits=visits,
    )

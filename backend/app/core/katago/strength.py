"""Maps UI rank strings to KataGo humanSLProfile + maxVisits.

The Human-SL model (b18c384nbt-humanv0) simulates real human play at each rank.
`maxVisits` adds tree search on top; higher = stronger.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrengthConfig:
    rank: str
    human_sl_profile: str
    max_visits: int


_RANK_TABLE: dict[str, StrengthConfig] = {
    "18k": StrengthConfig("18k", "rank_18k", 1),
    "15k": StrengthConfig("15k", "rank_15k", 1),
    "12k": StrengthConfig("12k", "rank_12k", 1),
    "10k": StrengthConfig("10k", "rank_10k", 2),
    "7k":  StrengthConfig("7k",  "rank_7k",  4),
    "5k":  StrengthConfig("5k",  "rank_5k",  8),
    "3k":  StrengthConfig("3k",  "rank_3k",  16),
    "1k":  StrengthConfig("1k",  "rank_1k",  32),
    "1d":  StrengthConfig("1d",  "rank_1d",  64),
    "3d":  StrengthConfig("3d",  "rank_3d",  128),
    "5d":  StrengthConfig("5d",  "rank_5d",  256),
    "7d":  StrengthConfig("7d",  "rank_7d",  512),
}

SUPPORTED_RANKS: tuple[str, ...] = tuple(_RANK_TABLE.keys())


def rank_to_config(rank: str) -> StrengthConfig:
    """Look up strength config for a UI rank string. Raises KeyError if unknown."""
    if rank not in _RANK_TABLE:
        raise KeyError(f"Unsupported rank: {rank!r}. Supported: {SUPPORTED_RANKS}")
    return _RANK_TABLE[rank]

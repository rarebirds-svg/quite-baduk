import pytest
from app.core.katago.strength import SUPPORTED_RANKS, rank_to_config


def test_all_ranks_present():
    expected = ["18k","15k","12k","10k","7k","5k","3k","1k","1d","3d","5d","7d"]
    assert list(SUPPORTED_RANKS) == expected


@pytest.mark.parametrize("rank,profile,visits", [
    ("18k", "rank_18k", 1),
    ("15k", "rank_15k", 1),
    ("12k", "rank_12k", 1),
    ("10k", "rank_10k", 2),
    ("7k",  "rank_7k",  4),
    ("5k",  "rank_5k",  8),
    ("3k",  "rank_3k",  16),
    ("1k",  "rank_1k",  32),
    ("1d",  "rank_1d",  64),
    ("3d",  "rank_3d",  128),
    ("5d",  "rank_5d",  256),
    ("7d",  "rank_7d",  512),
])
def test_rank_mapping(rank: str, profile: str, visits: int) -> None:
    cfg = rank_to_config(rank)
    assert cfg.rank == rank
    assert cfg.human_sl_profile == profile
    assert cfg.max_visits == visits


def test_unknown_rank_raises():
    with pytest.raises(KeyError):
        rank_to_config("100k")


def test_config_frozen():
    cfg = rank_to_config("5k")
    with pytest.raises(Exception):
        cfg.rank = "1d"  # type: ignore[misc]

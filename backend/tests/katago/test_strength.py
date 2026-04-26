import pytest

from app.core.katago.strength import SUPPORTED_RANKS, rank_to_config


def test_all_ranks_present():
    expected = [
        "9k", "8k", "7k", "6k", "5k", "4k", "3k", "2k", "1k",
        "1d", "2d", "3d", "4d", "5d", "6d", "7d", "8d", "9d",
    ]
    assert list(SUPPORTED_RANKS) == expected


@pytest.mark.parametrize("rank,profile,visits", [
    ("9k",  "rank_9k",  2),
    ("8k",  "rank_8k",  3),
    ("7k",  "rank_7k",  4),
    ("6k",  "rank_6k",  6),
    ("5k",  "rank_5k",  8),
    ("4k",  "rank_4k",  12),
    ("3k",  "rank_3k",  16),
    ("2k",  "rank_2k",  24),
    ("1k",  "rank_1k",  32),
    ("1d",  "rank_1d",  64),
    ("2d",  "rank_2d",  96),
    ("3d",  "rank_3d",  128),
    ("4d",  "rank_4d",  192),
    ("5d",  "rank_5d",  256),
    ("6d",  "rank_6d",  384),
    ("7d",  "rank_7d",  512),
    ("8d",  "rank_8d",  768),
    ("9d",  "rank_9d",  1024),
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
    # frozen dataclass -> dataclasses.FrozenInstanceError (subclass of AttributeError)
    with pytest.raises(AttributeError):
        cfg.rank = "1d"  # type: ignore[misc]

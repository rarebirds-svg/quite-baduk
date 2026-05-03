import pytest

from app.core.katago.strength import (
    SUPPORTED_AI_RANKS,
    SUPPORTED_RANKS,
    UnsupportedRank,
    rank_to_config,
)


def test_all_ranks_present():
    # SUPPORTED_RANKS is the full visit table — covers v1.0 + (currently
    # gated) higher-strength entries used by exhaustive style/player tests.
    expected = [
        "18k", "15k", "12k", "10k",
        "9k", "8k", "7k", "6k", "5k", "4k", "3k", "2k", "1k",
        "1d", "2d", "3d", "4d", "5d", "6d", "7d", "8d", "9d",
    ]
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
])
def test_rank_mapping(rank: str, profile: str, visits: int) -> None:
    cfg = rank_to_config(rank)
    assert cfg.rank == rank
    assert cfg.human_sl_profile == profile
    assert cfg.max_visits == visits


def test_unknown_rank_raises():
    # Anything outside SUPPORTED_AI_RANKS raises UnsupportedRank
    # (a ValueError subclass).
    with pytest.raises(UnsupportedRank):
        rank_to_config("100k")
    assert "100k" not in SUPPORTED_AI_RANKS


def test_config_frozen():
    cfg = rank_to_config("5k")
    # frozen dataclass -> dataclasses.FrozenInstanceError (subclass of AttributeError)
    with pytest.raises(AttributeError):
        cfg.rank = "1d"  # type: ignore[misc]


@pytest.mark.parametrize("rank", ["2d", "4d", "6d", "7d", "8d", "9d", "9k", "8k", "6k", "4k", "2k"])
def test_deprecated_ranks_raise_via_public_api(rank: str) -> None:
    """Ranks present in the visit table but withheld from v1.0's public set
    must raise UnsupportedRank when callers go through ``rank_to_config``."""
    with pytest.raises(UnsupportedRank):
        rank_to_config(rank)


def test_rank_to_config_caps_max_visits_at_256() -> None:
    """Every supported rank must have max_visits <= 256 in v1.0."""
    from app.core.katago.strength import (
        SUPPORTED_AI_RANKS,
        rank_to_config,
    )

    for rank in SUPPORTED_AI_RANKS:
        cfg = rank_to_config(rank, "balanced", None)
        assert cfg.max_visits <= 256, (
            f"{rank} exceeds the v1.0 cap (got {cfg.max_visits})"
        )


def test_supported_ranks_excludes_6d_and_7d() -> None:
    from app.core.katago.strength import SUPPORTED_AI_RANKS

    assert "6d" not in SUPPORTED_AI_RANKS
    assert "7d" not in SUPPORTED_AI_RANKS
    assert "5d" in SUPPORTED_AI_RANKS


def test_unsupported_rank_raises() -> None:
    from app.core.katago.strength import UnsupportedRank, rank_to_config

    with pytest.raises(UnsupportedRank):
        rank_to_config("9d", "balanced", None)

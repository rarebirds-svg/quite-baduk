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
    ("4d",  "rank_4d",  128),
    # 5d..9d ride the v1.0 cap — base table is higher but min(128, …)
    # in rank_to_config keeps them at 128.
    ("5d",  "rank_5d",  128),
    ("6d",  "rank_6d",  128),
    ("7d",  "rank_7d",  128),
    ("8d",  "rank_8d",  128),
    ("9d",  "rank_9d",  128),
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


@pytest.mark.parametrize("rank", ["18k", "15k", "12k", "10k"])
def test_deprecated_ranks_raise_via_public_api(rank: str) -> None:
    """Ranks present in the visit table but withheld from v1.0's public set
    must raise UnsupportedRank when callers go through ``rank_to_config``.
    The public set is 9k..9d; 18k..10k are gated as too-easy floor."""
    with pytest.raises(UnsupportedRank):
        rank_to_config(rank)


def test_rank_to_config_caps_max_visits_at_128() -> None:
    """Every supported rank x style must have max_visits <= 128 in v1.0."""
    from app.core.katago.strength import (
        SUPPORTED_AI_RANKS,
        rank_to_config,
    )
    from app.core.katago.style import SUPPORTED_STYLES

    for rank in SUPPORTED_AI_RANKS:
        for style in SUPPORTED_STYLES:
            cfg = rank_to_config(rank, style, None)
            assert cfg.max_visits <= 128, (
                f"{rank} x {style} exceeds the v1.0 cap (got {cfg.max_visits})"
            )
            assert cfg.max_visits >= 1, (
                f"{rank} x {style} fell below the floor (got {cfg.max_visits})"
            )


def test_supported_ranks_spans_9k_through_9d() -> None:
    from app.core.katago.strength import SUPPORTED_AI_RANKS

    # The full 9k..9d ladder is in. 18k..10k stay out (too-easy floor).
    for r in (
        "9k", "8k", "7k", "6k", "5k", "4k", "3k", "2k", "1k",
        "1d", "2d", "3d", "4d", "5d", "6d", "7d", "8d", "9d",
    ):
        assert r in SUPPORTED_AI_RANKS, f"{r} should be in the public set"
    for r in ("18k", "15k", "12k", "10k"):
        assert r not in SUPPORTED_AI_RANKS, f"{r} should be gated out"


def test_floor_rank_raises() -> None:
    """Below-9k floor remains gated."""
    from app.core.katago.strength import UnsupportedRank, rank_to_config

    with pytest.raises(UnsupportedRank):
        rank_to_config("18k", "balanced", None)

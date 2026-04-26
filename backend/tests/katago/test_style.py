"""Tests for the style (기풍) → humanSLProfile / visits mapping.

Contract (post-fix):
  - Every resolved profile must contain the user's chosen rank (rank_{R} or
    preaz_{R}), so KataGo's move prior matches the rank the user selected.
  - Style and player affect which *family* (rank_ vs preaz_) and the visits
    budget multiplier. They never override the rank in the profile string.
"""

from __future__ import annotations

from app.core.katago.strength import SUPPORTED_RANKS, rank_to_config
from app.core.katago.style import STYLES, SUPPORTED_STYLES


def test_default_style_is_balanced_and_uses_rank_profile():
    cfg = rank_to_config("5k")
    assert cfg.human_sl_profile == "rank_5k"
    assert cfg.max_visits == 8  # balanced = 1.0x baseline


def test_territorial_uses_preaz_and_bumps_visits():
    cfg = rank_to_config("5k", "territorial")
    assert cfg.human_sl_profile == "preaz_5k"
    assert cfg.max_visits == 10  # 8 * 1.25 = 10


def test_influence_uses_preaz_and_honours_rank():
    cfg_5k = rank_to_config("5k", "influence")
    cfg_7d = rank_to_config("7d", "influence")
    assert cfg_5k.human_sl_profile == "preaz_5k"
    assert cfg_7d.human_sl_profile == "preaz_7d"


def test_classical_uses_preaz_and_honours_rank():
    cfg_5k = rank_to_config("5k", "classical")
    cfg_1d = rank_to_config("1d", "classical")
    assert cfg_5k.human_sl_profile == "preaz_5k"
    assert cfg_1d.human_sl_profile == "preaz_1d"


def test_combative_amplifies_visits():
    cfg = rank_to_config("5k", "combative")
    assert cfg.human_sl_profile == "rank_5k"
    assert cfg.max_visits == 14  # 8 * 1.75 = 14


def test_speed_reduces_visits_but_stays_at_least_one():
    cfg = rank_to_config("9k", "speed")
    assert cfg.max_visits >= 1  # 2 * 0.5 clamps to >= 1


def test_unknown_style_falls_back_to_balanced():
    cfg = rank_to_config("5k", "not-a-real-style")
    assert cfg.human_sl_profile == "rank_5k"


def test_every_style_resolves_for_every_rank_with_rank_in_profile():
    # Exhaustive guard: every style at every rank must produce a profile that
    # carries the rank — no proyear_YEAR leaks that would ignore the user's
    # rank choice.
    for rank in SUPPORTED_RANKS:
        for style in SUPPORTED_STYLES:
            cfg = rank_to_config(rank, style)
            assert cfg.rank == rank
            assert cfg.max_visits >= 1
            assert cfg.human_sl_profile  # non-empty
            assert "{rank}" not in cfg.human_sl_profile
            # Rank-conformance: the profile must mention the chosen rank.
            assert cfg.human_sl_profile.endswith(f"_{rank}"), (
                f"style={style} rank={rank} produced {cfg.human_sl_profile!r} "
                "which does not honour the rank"
            )
            # And the family must be one of the two rank-aware prefixes.
            assert cfg.human_sl_profile.startswith(("rank_", "preaz_")), (
                f"style={style} rank={rank} produced {cfg.human_sl_profile!r} "
                "which is not a rank-aware family"
            )


def test_all_styles_have_profiles_in_style_table():
    assert set(STYLES.keys()) == set(SUPPORTED_STYLES)


# ─── player resolution ────────────────────────────────────────────────────


def test_player_profile_follows_rank_not_proyear():
    # Lee Sedol — combative style. Picking him at 5k must play 5k-level,
    # not 2012-pro-level.
    cfg = rank_to_config("5k", "balanced", "lee_sedol")
    assert cfg.human_sl_profile == "rank_5k"  # combative template = rank_{rank}
    # Combative visits multiplier still applies: 8 * 1.75 = 14.
    assert cfg.max_visits == 14


def test_player_style_wins_over_passed_style():
    # Passed style="territorial" but player="lee_sedol" (combative).
    # The player's STYLE wins — so profile family + visits come from combative.
    cfg = rank_to_config("5k", "territorial", "lee_sedol")
    assert cfg.human_sl_profile == "rank_5k"  # combative
    assert cfg.max_visits == 14  # 1.75x


def test_unknown_player_falls_back_to_passed_style():
    cfg = rank_to_config("5k", "territorial", "not-a-real-player")
    assert cfg.human_sl_profile == "preaz_5k"


def test_every_player_produces_rank_aware_profile_for_every_rank():
    from app.core.katago.players import SUPPORTED_PLAYERS

    for rank in SUPPORTED_RANKS:
        for player_id in SUPPORTED_PLAYERS:
            cfg = rank_to_config(rank, "balanced", player_id)
            assert cfg.human_sl_profile.startswith(("rank_", "preaz_")), (
                f"player={player_id} rank={rank} produced "
                f"{cfg.human_sl_profile!r} which is not rank-aware"
            )
            assert cfg.human_sl_profile.endswith(f"_{rank}"), (
                f"player={player_id} rank={rank} produced "
                f"{cfg.human_sl_profile!r} which does not honour the rank"
            )
            assert "{rank}" not in cfg.human_sl_profile
            assert cfg.max_visits >= 1


def test_influence_player_at_low_rank_stays_at_that_rank():
    # Regression for the reported bug: picking Takemiya (influence) at 7k
    # must play 7k moves, not 1985-pro moves.
    cfg = rank_to_config("7k", "balanced", "takemiya_masaki")
    assert cfg.human_sl_profile == "preaz_7k"  # influence -> preaz_{rank}
    assert cfg.max_visits == 4  # base(7k)=4 * 1.0 = 4


def test_classical_player_at_low_rank_stays_at_that_rank():
    cfg = rank_to_config("9k", "balanced", "go_seigen")
    assert cfg.human_sl_profile == "preaz_9k"  # classical -> preaz_{rank}
    assert cfg.max_visits == 2  # base(9k)=2 * 1.0 = 2

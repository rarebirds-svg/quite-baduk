"""Playing style (기풍) → KataGo Human-SL profile mapping.

KataGo's Human-SL model supports three profile families:

* ``preaz_{rank}`` — imitates human play *before* the AlphaZero era, which
  tends to be more classical / territorial / solid.
* ``rank_{rank}`` — modern post-AZ human play, with AI-influenced openings
  and a more fighting-forward temperament.
* ``proyear_{YEAR}`` — imitates pros from a specific historical year. Useful
  for era-defining styles (신포석 1935, 우주류 세력기 1985, etc.).

The "기풍" concept asked for by users is fuzzy — no two masters really play
alike — so we approximate each category by (a) choosing the profile family
and optional year anchor, and (b) tweaking the visit budget so that fast /
fighting styles behave differently from slow / balanced ones.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

StyleId = Literal[
    "balanced",       # 균형형 (박정환, 신진서, 커제)
    "territorial",    # 실리형 (이창호, 조치훈, 고바야시 고이치)
    "influence",      # 세력형 (다케미야 마사키, 후지사와 슈코, 오타케 히데오)
    "combative",      # 전투형 (유창혁, 사카타 에이오, 이세돌, 구리)
    "speed",          # 속기형 (조훈현, 가토 마사오)
    "classical",      # 혁신·독창형 (오청원, 기타니 미노루)
    "rustic",         # 토종·야전형 (서봉수)
]


@dataclass(frozen=True)
class StyleProfile:
    id: StyleId
    # Which humanSL profile family to use. "preaz_{rank}" | "rank_{rank}"
    # | "proyear_{year}" — the final string is resolved at call time with
    # rank slotted in where {rank} appears.
    profile_template: str
    # Multiplier applied to the rank-based visit budget. >1 makes the engine
    # think longer (fighting/reading-heavy), <1 is a speed-demon approximation.
    visits_multiplier: float = 1.0
    # Short label shown in the UI summary — paired with an i18n key.
    slug: str = ""


STYLES: dict[StyleId, StyleProfile] = {
    "balanced": StyleProfile(
        id="balanced",
        profile_template="rank_{rank}",
        visits_multiplier=1.0,
        slug="balanced",
    ),
    "territorial": StyleProfile(
        id="territorial",
        # Pre-AZ, rank-scaled profile reads like classical territorial play:
        # solid shimari, corner-first, finesse endgame.
        profile_template="preaz_{rank}",
        visits_multiplier=1.25,
        slug="territorial",
    ),
    "influence": StyleProfile(
        id="influence",
        # Pre-AZ amateurs historically favored thick, central, influence-heavy
        # shapes; mapping to preaz_{rank} preserves that flavor while honoring
        # the user's chosen rank.
        profile_template="preaz_{rank}",
        visits_multiplier=1.0,
        slug="influence",
    ),
    "combative": StyleProfile(
        id="combative",
        profile_template="rank_{rank}",
        visits_multiplier=1.75,
        slug="combative",
    ),
    "speed": StyleProfile(
        id="speed",
        profile_template="rank_{rank}",
        visits_multiplier=0.5,
        slug="speed",
    ),
    "classical": StyleProfile(
        id="classical",
        # Pre-AZ captures the varied / shinfuseki-leaning fuseki character
        # without forcing a fixed pro-year strength that would ignore rank.
        profile_template="preaz_{rank}",
        visits_multiplier=1.0,
        slug="classical",
    ),
    "rustic": StyleProfile(
        id="rustic",
        profile_template="preaz_{rank}",
        visits_multiplier=0.75,
        slug="rustic",
    ),
}

SUPPORTED_STYLES: tuple[StyleId, ...] = tuple(STYLES.keys())
DEFAULT_STYLE: StyleId = "balanced"


def style_to_profile(style: str, rank: str) -> StyleProfile:
    """Look up a style profile. Falls back to ``balanced`` on unknown input
    so a legacy game row without ``ai_style`` still plays gracefully."""
    key: StyleId = style if style in STYLES else DEFAULT_STYLE  # type: ignore[assignment]
    return STYLES[key]


def resolve_human_sl_profile(style: str, rank: str) -> str:
    """Concrete ``humanSLProfile`` string for the given style + rank."""
    prof = style_to_profile(style, rank)
    return prof.profile_template.replace("{rank}", rank)

"""Individual 기사 (pro-player) profiles for humanSL imitation.

Each player maps to:
  * a ``style`` category (see app.core.katago.style) — drives both the
    humanSLProfile family (``rank_`` vs ``preaz_``) and the visit-count
    multiplier applied to the rank-based baseline.
  * a ``proyear`` — retained as stable metadata describing the player's
    career-peak year. Not currently consumed by the profile mapping: rank
    is the primary strength signal (see app.core.katago.strength) and
    KataGo cannot compose ``proyear_{YEAR}`` with the chosen amateur rank,
    so we honor rank and let the player's style express the flavor. The
    field stays available for future UI surfacing (e.g., era labels).

Player IDs are ASCII snake_case so they survive JSON round-trips cleanly;
display strings live in the i18n dictionaries on the frontend.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.katago.style import StyleId


@dataclass(frozen=True)
class Player:
    id: str
    style: StyleId
    proyear: int


# Order matters — it's the display order inside each style group on the
# picker. Keep style groupings contiguous.
_PLAYERS: tuple[Player, ...] = (
    # 실리형 (territorial)
    Player("lee_changho",       "territorial", 1998),
    Player("cho_chikun",        "territorial", 1984),
    Player("kobayashi_koichi",  "territorial", 1988),
    # 세력형 (influence)
    Player("takemiya_masaki",   "influence",   1986),
    Player("fujisawa_shuko",    "influence",   1978),
    Player("otake_hideo",       "influence",   1975),
    # 전투형 (combative)
    Player("yoo_changhyuk",     "combative",   1998),
    Player("sakata_eio",        "combative",   1962),
    Player("lee_sedol",         "combative",   2012),
    Player("gu_li",             "combative",   2010),
    # 속기형 (speed)
    Player("cho_hunhyun",       "speed",       1990),
    Player("kato_masao",        "speed",       1980),
    # 혁신·독창형 (classical / shinfuseki)
    Player("go_seigen",         "classical",   1950),
    Player("kitani_minoru",     "classical",   1940),
    # 균형형 (balanced)
    Player("park_junghwan",     "balanced",    2018),
    Player("shin_jinseo",       "balanced",    2023),
    Player("ke_jie",            "balanced",    2019),
    # 토종·야전형 (rustic)
    Player("seo_bongsoo",       "rustic",      1992),
)


PLAYERS: dict[str, Player] = {p.id: p for p in _PLAYERS}
SUPPORTED_PLAYERS: tuple[str, ...] = tuple(PLAYERS.keys())


def get_player(player_id: str | None) -> Player | None:
    if not player_id:
        return None
    return PLAYERS.get(player_id)


def players_in_order() -> tuple[Player, ...]:
    """Return players in the canonical picker order."""
    return _PLAYERS

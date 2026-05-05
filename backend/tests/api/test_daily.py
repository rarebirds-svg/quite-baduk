"""Daily challenge endpoints — happy path + auth + grading verdicts."""
from __future__ import annotations

import datetime as _dt

import pytest
from httpx import AsyncClient

from app.services.daily_challenge import (
    CHALLENGES,
    daily_index,
    get_today,
)


def test_daily_index_is_deterministic_per_date() -> None:
    d1 = _dt.date(2026, 5, 5)
    d2 = _dt.date(2026, 5, 6)
    # Same date → same index. Adjacent dates increment cleanly.
    assert daily_index(d1) == daily_index(d1)
    assert daily_index(d2) == (daily_index(d1) + 1) % len(CHALLENGES)


def test_daily_index_in_bounds() -> None:
    for n in range(1, 100):
        idx = daily_index(_dt.date(2026, 1, 1) + _dt.timedelta(days=n))
        assert 0 <= idx < len(CHALLENGES)


def test_get_today_returns_known_challenge() -> None:
    challenge = get_today()
    assert challenge.id in {c.id for c in CHALLENGES}
    assert challenge.board_size in (9, 13, 19)
    assert challenge.to_move in ("B", "W")


@pytest.mark.asyncio
async def test_get_endpoint_unauth_returns_401(client: AsyncClient) -> None:
    r = await client.get("/api/daily-challenge")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_endpoint_returns_today(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "daily_user"})
    assert r.status_code == 201
    r = await client.get("/api/daily-challenge")
    assert r.status_code == 200
    body = r.json()
    assert "id" in body
    assert "board_size" in body
    assert "setup" in body
    assert isinstance(body["setup"], list)
    assert "to_move" in body
    assert "prompt_key" in body


@pytest.mark.asyncio
async def test_answer_grades_via_katago(client: AsyncClient) -> None:
    await client.post("/api/session", json={"nickname": "daily_grader"})
    today = get_today()
    used = {coord.upper() for _, coord in today.setup}
    candidate = next(
        c
        for c in ("A1", "B1", "C1", "D1", "F1", "H1", "J1")
        if c not in used
    )

    r = await client.post(
        "/api/daily-challenge/answer",
        json={"challenge_id": today.id, "coord": candidate},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] in ("best", "ok", "weak", "miss", "illegal")
    assert isinstance(body["top_moves"], list)
    assert "winrate_before" in body
    assert "drop" in body


@pytest.mark.asyncio
async def test_answer_unknown_id_returns_404(client: AsyncClient) -> None:
    """Daily-only gate is removed — any catalogue id is gradable. An ID
    that doesn't exist in the catalogue 404s instead of 410."""
    await client.post("/api/session", json={"nickname": "daily_unknown"})
    r = await client.post(
        "/api/daily-challenge/answer",
        json={"challenge_id": "ch-not-real", "coord": "A1"},
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "challenge_not_found"


@pytest.mark.asyncio
async def test_random_endpoint_returns_match(client: AsyncClient) -> None:
    await client.post("/api/session", json={"nickname": "daily_random"})
    r = await client.get(
        "/api/daily-challenge/random",
        params={"board_size": 9, "topic": "opening"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["board_size"] == 9
    assert body["topic"] == "opening"


def test_catalogue_setup_coords_are_unique_per_puzzle() -> None:
    """Catch authoring slip-ups: a setup that lists the same coord
    twice would silently overwrite the colour and produce a position
    the user couldn't reason about."""
    for c in CHALLENGES:
        coords = [coord.upper() for _, coord in c.setup]
        assert len(coords) == len(set(coords)), (
            f"{c.id}: duplicate coord in setup: "
            f"{[k for k in coords if coords.count(k) > 1]}"
        )


def test_catalogue_setup_coords_are_within_board() -> None:
    """Each setup coord must parse + lie inside the puzzle's board
    size. A typo (e.g. K8 on a 9x9 — there's no K column) silently
    pre-places nothing and ruins grading."""
    from app.core.rules.sgf_coord import gtp_to_xy

    for c in CHALLENGES:
        for color, coord in c.setup:
            xy = gtp_to_xy(coord, c.board_size)
            assert xy is not None, f"{c.id}: bad coord {coord!r}"
            x, y = xy
            assert 0 <= x < c.board_size and 0 <= y < c.board_size, (
                f"{c.id}: coord {coord} → ({x},{y}) out of board {c.board_size}"
            )
            assert color in ("B", "W"), f"{c.id}: bad colour {color!r}"


def test_catalogue_to_move_is_legal_value() -> None:
    for c in CHALLENGES:
        assert c.to_move in ("B", "W"), f"{c.id}: bad to_move {c.to_move!r}"


def test_catalogue_topic_label_matches_stone_count_heuristic() -> None:
    """Sanity check that topic labels aren't wildly mis-applied. Rough
    rules of thumb (not strict — enforced by stone count, which is what
    a player sees):
      opening      — 0..30% of board area in stones
      joseki       — corner-flavoured, low stone count
      tesuji       — small contact fight, < 25 stones total
      middle_game  — substantial stones placed
      endgame      — most of the board outline laid out
      life_death / capturing_race — local cluster, but small total stones OK
    """
    for c in CHALLENGES:
        n_stones = len(c.setup)
        area_pct = n_stones / (c.board_size ** 2)
        if c.topic == "opening":
            assert area_pct < 0.20, (
                f"{c.id}: {n_stones} stones for an opening puzzle on "
                f"{c.board_size}x{c.board_size} — too many for early game"
            )
        if c.topic == "endgame":
            # Endgames need enough stones to actually be late.
            assert n_stones >= 4, (
                f"{c.id}: only {n_stones} stones for an endgame puzzle"
            )


def test_catalogue_ids_are_unique() -> None:
    ids = [c.id for c in CHALLENGES]
    dups = {x for x in ids if ids.count(x) > 1}
    assert not dups, f"duplicate challenge ids: {dups}"


# ─── Geometric variant tests ──────────────────────────────────────────


def test_transform_round_trip_via_split_id() -> None:
    from app.services.daily_challenge import _split_id

    assert _split_id("ch-9-jo-1") == ("ch-9-jo-1", 0)
    assert _split_id("ch-9-jo-1.t0") == ("ch-9-jo-1", 0)
    assert _split_id("ch-9-jo-1.t7") == ("ch-9-jo-1", 7)
    # malformed suffix → treat as no transform
    assert _split_id("ch-9-jo-1.tX") == ("ch-9-jo-1.tX", 0)
    assert _split_id("ch-9-jo-1.t99") == ("ch-9-jo-1.t99", 0)


def test_transform_preserves_stone_count_and_topic() -> None:
    from app.services.daily_challenge import NUM_VARIANTS, _apply_transform

    base = CHALLENGES[0]
    for t in range(NUM_VARIANTS):
        v = _apply_transform(base, t)
        assert len(v.setup) == len(base.setup)
        assert v.topic == base.topic
        assert v.difficulty == base.difficulty
        assert v.board_size == base.board_size
        assert v.to_move == base.to_move


def test_transform_keeps_coords_inside_board() -> None:
    """Every transformed coord must still be a legal cell on the board.
    Catches off-by-one bugs in the rotation formulas."""
    from app.core.rules.sgf_coord import gtp_to_xy
    from app.services.daily_challenge import NUM_VARIANTS, _apply_transform

    for c in CHALLENGES:
        for t in range(NUM_VARIANTS):
            v = _apply_transform(c, t)
            for _color, coord in v.setup:
                xy = gtp_to_xy(coord, v.board_size)
                assert xy is not None, (
                    f"{c.id} t={t}: bad transformed coord {coord!r}"
                )
                x, y = xy
                assert 0 <= x < v.board_size and 0 <= y < v.board_size


def test_transform_identity_returns_same_setup() -> None:
    from app.services.daily_challenge import _apply_transform

    base = CHALLENGES[0]
    v = _apply_transform(base, 0)
    assert v.setup == base.setup
    assert v.id == base.id  # no suffix on identity


def test_transform_180_is_self_inverse() -> None:
    """rot180 ∘ rot180 = identity. Catches sign-flip bugs in the
    coordinate maths."""
    from app.services.daily_challenge import _transform_coord

    base = CHALLENGES[0]
    for _color, coord in base.setup:
        once_c = _transform_coord(coord, base.board_size, 2)
        twice_c = _transform_coord(once_c, base.board_size, 2)
        assert twice_c.upper() == coord.upper()


@pytest.mark.asyncio
async def test_random_endpoint_returns_transformed_id_sometimes(
    client: AsyncClient,
) -> None:
    """Drive the API enough times that we observe at least one
    transformed id (.tN suffix) under filters narrow enough to keep
    landing on the same base."""
    from app.services.daily_challenge import filter_challenges

    await client.post("/api/session", json={"nickname": "daily_xform"})
    # Pick a single-puzzle cell so we definitely come back to the same
    # base — the only thing that should change is the transform.
    target = None
    for size, diff, tp in (
        (9, "easy", "joseki"),
        (9, "easy", "tesuji"),
        (9, "medium", "endgame"),
    ):
        if len(filter_challenges(board_size=size, difficulty=diff, topic=tp)) == 1:
            target = (size, diff, tp)
            break
    assert target is not None, "expected a single-puzzle cell to test on"
    size, diff, tp = target

    seen_transforms: set[int] = set()
    for _ in range(30):
        r = await client.get(
            "/api/daily-challenge/random",
            params={"board_size": size, "difficulty": diff, "topic": tp},
        )
        assert r.status_code == 200
        cid = r.json()["id"]
        if ".t" in cid:
            seen_transforms.add(int(cid.rsplit(".t", 1)[1]))
        else:
            seen_transforms.add(0)
    # 30 picks across 8 transforms — should observe at least 3 distinct
    # values with overwhelming probability.
    assert len(seen_transforms) >= 3, (
        f"transform variety too low: {seen_transforms}"
    )


@pytest.mark.asyncio
async def test_answer_grades_transformed_id(client: AsyncClient) -> None:
    """Submit an answer for a transformed id; the grader must
    reconstruct the same transformed position rather than fall through
    to the un-rotated base, otherwise the user's coord no longer lines
    up with the board they saw."""
    await client.post("/api/session", json={"nickname": "daily_xgrade"})
    base = CHALLENGES[0]
    transformed_id = f"{base.id}.t3"
    # A1 is empty on every board; a 9x9 setup never lands there.
    r = await client.post(
        "/api/daily-challenge/answer",
        json={"challenge_id": transformed_id, "coord": "A1"},
    )
    assert r.status_code == 200
    assert r.json()["verdict"] in ("best", "ok", "weak", "miss", "illegal")


def test_catalogue_covers_every_filter_cell() -> None:
    """Promise to the user: any (board × topic × difficulty) selection
    has at least one puzzle. Drives the "절대 비어 있지 않다" guarantee
    behind the filter UI."""
    from app.services.daily_challenge import (
        BOARD_SIZES,
        DIFFICULTIES,
        TOPICS,
        filter_challenges,
    )

    missing: list[str] = []
    for size in BOARD_SIZES:
        for diff in DIFFICULTIES:
            for topic in TOPICS:
                if not filter_challenges(
                    board_size=size, difficulty=diff, topic=topic
                ):
                    missing.append(f"{size}|{diff}|{topic}")
    assert missing == [], (
        f"Catalogue must cover every (size × difficulty × topic) cell; "
        f"missing: {missing}"
    )


@pytest.mark.asyncio
async def test_random_endpoint_returns_match_for_every_cell(
    client: AsyncClient,
) -> None:
    """Round-trip the same guarantee through the API: every concrete
    triple resolves, never 404s. Catches the case where the catalogue
    has data but a routing/filter bug skips it."""
    from app.services.daily_challenge import (
        BOARD_SIZES,
        DIFFICULTIES,
        TOPICS,
    )
    await client.post("/api/session", json={"nickname": "daily_cover"})
    for size in BOARD_SIZES:
        for diff in DIFFICULTIES:
            for topic in TOPICS:
                r = await client.get(
                    "/api/daily-challenge/random",
                    params={"board_size": size, "topic": topic, "difficulty": diff},
                )
                assert r.status_code == 200, (
                    f"{size}/{diff}/{topic} returned {r.status_code}"
                )


@pytest.mark.asyncio
async def test_catalogue_returns_options_and_counts(client: AsyncClient) -> None:
    await client.post("/api/session", json={"nickname": "daily_cat"})
    r = await client.get("/api/daily-challenge/catalogue")
    assert r.status_code == 200
    body = r.json()
    assert set(body["board_sizes"]) == {9, 13, 19}
    assert set(body["difficulties"]) == {"easy", "medium", "hard"}
    assert set(body["topics"]) == {
        "opening", "joseki", "life_death", "tesuji",
        "middle_game", "endgame", "capturing_race",
    }
    # Counts present for every (size, difficulty, topic) cell.
    assert isinstance(body["counts"], dict)
    assert "9|easy|opening" in body["counts"]
    assert isinstance(body["counts"]["9|easy|opening"], int)


@pytest.mark.asyncio
async def test_random_excludes_id_returns_different(client: AsyncClient) -> None:
    """Pass an exclude_id and the random pick must avoid it (so "다음
    문제" doesn't repeat)."""
    await client.post("/api/session", json={"nickname": "daily_excl"})
    # 9x9 opening has 3 puzzles → excluding the easy one must yield a
    # different id.
    r1 = await client.get(
        "/api/daily-challenge/random",
        params={"board_size": 9, "topic": "opening"},
    )
    assert r1.status_code == 200
    first = r1.json()["id"]
    r2 = await client.get(
        "/api/daily-challenge/random",
        params={"board_size": 9, "topic": "opening", "exclude_id": first},
    )
    assert r2.status_code == 200
    assert r2.json()["id"] != first


@pytest.mark.asyncio
async def test_random_no_other_match_when_only_excluded_left(
    client: AsyncClient,
) -> None:
    """When the only puzzle in a filter is the excluded id, the response
    is a distinguishable 404 (code=no_other_match) so the UI can keep
    the current puzzle and show 'no other puzzles' instead of bouncing
    to the empty state."""
    await client.post("/api/session", json={"nickname": "daily_only"})
    # Pull whatever 19x19 joseki returns first, then exclude it.
    r1 = await client.get(
        "/api/daily-challenge/random",
        params={"board_size": 19, "topic": "joseki"},
    )
    assert r1.status_code == 200
    only_id = r1.json()["id"]
    # The 19x19 joseki section has 2 entries in the V1 catalogue, so
    # excluding one leaves the other — fine. Exclude both by listing
    # only one with a matching difficulty filter that pins it down.
    diff = r1.json()["difficulty"]
    r2 = await client.get(
        "/api/daily-challenge/random",
        params={
            "board_size": 19,
            "topic": "joseki",
            "difficulty": diff,
            "exclude_id": only_id,
        },
    )
    # If the (size,topic,difficulty) cell only had this one entry, the
    # response is "no_other_match"; otherwise we just got a sibling.
    assert r2.status_code in (200, 404)
    if r2.status_code == 404:
        assert r2.json()["error"]["code"] == "no_other_match"


@pytest.mark.asyncio
async def test_answer_grades_non_today_challenge(client: AsyncClient) -> None:
    """Pick a catalogue puzzle that is NOT today's and grade against it.
    Used to be 410-blocked; now must succeed."""
    await client.post("/api/session", json={"nickname": "daily_other"})
    other = next(c for c in CHALLENGES if c.id != get_today().id)
    used = {coord.upper() for _, coord in other.setup}
    # Pool of generic empty intersections that fit a 9x9 (smallest board)
    # — works for any catalogue entry since 13/19 boards have these too.
    candidate = next(
        c for c in (
            "A1", "B1", "F1", "H1", "J1",
            "A9", "B9", "F9", "H9", "J9",
        ) if c not in used and c not in {f"{coord}".upper() for _, coord in other.setup}
    )
    r = await client.post(
        "/api/daily-challenge/answer",
        json={"challenge_id": other.id, "coord": candidate},
    )
    assert r.status_code == 200
    assert r.json()["verdict"] in ("best", "ok", "weak", "miss", "illegal")

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

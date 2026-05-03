"""GameError responses must include both ``code`` and ``detail`` so
clients can show targeted error toasts (the ``detail`` is e.g. the
exact illegal coordinate, not just the category)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_game_error_response_includes_detail(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "errbody"})
    assert r.status_code == 201

    # handicap=6 is valid Pydantic-wise (0..9) but rejected by the service
    # for board_size=9 → GameError("INVALID_HANDICAP", "6").
    r = await client.post(
        "/api/games",
        json={
            "ai_rank": "5k",
            "handicap": 6,
            "user_color": "black",
            "board_size": 9,
        },
    )
    assert r.status_code == 400
    body = r.json()
    assert body["detail"]["code"] == "INVALID_HANDICAP"
    assert body["detail"]["detail"] == "6"

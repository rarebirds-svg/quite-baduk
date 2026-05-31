# API datetime이 UTC 'Z'로 직렬화되는지 검증 — 프론트 로컬 오해석(9시간) 방지
import datetime as dt

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_game_started_at_serialized_with_utc_z(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "tzcheck"})
    assert r.status_code == 201, r.text
    r = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0, "user_color": "black"},
    )
    assert r.status_code == 201, r.text
    started = r.json()["started_at"]
    # 'Z' 표식이 있어야 JS new Date()가 UTC로 정확히 파싱한다(없으면 로컬로 오해석).
    assert started.endswith("Z"), f"expected UTC 'Z' suffix, got {started!r}"
    parsed = dt.datetime.fromisoformat(started.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    # 직렬화 값이 실제 UTC 현재 시각과 가까워야(naive를 로컬로 밀지 않았다는 의미).
    now = dt.datetime.now(dt.UTC)
    assert abs((now - parsed).total_seconds()) < 120


def test_utc_datetime_type_serializes_naive_as_utc() -> None:
    from pydantic import BaseModel

    from app.schemas.datetime_utc import UtcDatetime

    class M(BaseModel):
        ts: UtcDatetime
        opt: UtcDatetime | None = None

    naive = dt.datetime(2026, 5, 31, 8, 45, 0)  # SQLite func.now()가 주는 naive UTC
    out = M(ts=naive).model_dump(mode="json")
    assert out["ts"] == "2026-05-31T08:45:00Z"
    assert out["opt"] is None
    # 이미 tz-aware인 경우도 UTC 'Z'로 정규화
    aware = dt.datetime(2026, 5, 31, 8, 45, 0, tzinfo=dt.UTC)
    assert M(ts=aware).model_dump(mode="json")["ts"] == "2026-05-31T08:45:00Z"

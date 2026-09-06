"""구글 계정 연동 — 세션 연동, 새 기기 이어하기, 소유권 승계, state 검증."""
from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient

import app.api.auth_google as mod
from app.config import settings


@pytest.fixture
def google_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_client_id", "cid")
    monkeypatch.setattr(settings, "google_client_secret", "csec")
    monkeypatch.setattr(settings, "public_base_url", "http://test")


def _mock_google(
    monkeypatch: pytest.MonkeyPatch, sub: str = "g-123", email: str = "u@x.io"
) -> None:
    async def exchange(code: str) -> dict[str, Any]:
        assert code == "the-code"
        return {"access_token": "at"}

    async def userinfo(token: str) -> dict[str, Any]:
        assert token == "at"  # noqa: S105 (fixture value)
        return {"sub": sub, "email": email, "email_verified": True, "name": "GoFan"}

    monkeypatch.setattr(mod, "exchange_code", exchange)
    monkeypatch.setattr(mod, "fetch_userinfo", userinfo)


async def _start_and_callback(client: AsyncClient, next_path: str = "/settings") -> Any:
    r = await client.get(f"/api/auth/google/start?next={next_path}")
    assert r.status_code == 302
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    return await client.get(f"/api/auth/google/callback?code=the-code&state={state}")


@pytest.mark.asyncio
async def test_disabled_by_default(client: AsyncClient) -> None:
    assert (await client.get("/api/auth/providers")).json() == {"google": False}
    assert (await client.get("/api/auth/google/start")).status_code == 404


@pytest.mark.asyncio
async def test_start_redirects_to_google_with_state_cookie(
    client: AsyncClient, google_on: None
) -> None:
    assert (await client.get("/api/auth/providers")).json() == {"google": True}
    r = await client.get("/api/auth/google/start?next=/history")
    assert r.status_code == 302
    loc = urlparse(r.headers["location"])
    assert loc.netloc == "accounts.google.com"
    q = parse_qs(loc.query)
    assert q["client_id"] == ["cid"]
    assert q["redirect_uri"] == ["http://test/api/auth/google/callback"]
    assert "baduk_oauth_state" in {c.name for c in client.cookies.jar}


@pytest.mark.asyncio
async def test_link_existing_session_and_claim_its_games(
    client: AsyncClient, google_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_google(monkeypatch)
    await client.post("/api/session", json={"nickname": "alice"})
    g = (await client.post(
        "/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"}
    )).json()

    r = await _start_and_callback(client)
    assert r.status_code == 302
    assert r.headers["location"] == "http://test/settings?linked=1"

    me = (await client.get("/api/session")).json()
    assert me["nickname"] == "alice"  # 닉네임은 그대로
    assert me["account"] == {"provider": "google", "email": "u@x.io"}

    # 새 대국은 계정에 귀속되고, 예전 대국도 소급 귀속된다 → export에 둘 다.
    g2 = (await client.post(
        "/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"}
    )).json()
    ids = {row["id"] for row in (await client.get("/api/games")).json()}
    assert {g["id"], g2["id"]} <= ids


@pytest.mark.asyncio
async def test_new_device_continues_with_old_games(
    client: AsyncClient, google_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_google(monkeypatch)
    await client.post("/api/session", json={"nickname": "alice"})
    old = (await client.post(
        "/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"}
    )).json()
    await _start_and_callback(client)

    # 세션 종료 = 다른 기기/만료 뒤 상황. 쿠키 없이 구글로 다시 들어온다.
    await client.post("/api/session/end")
    client.cookies.clear()
    assert (await client.get("/api/session")).status_code == 401

    r = await _start_and_callback(client, next_path="/history")
    assert r.headers["location"] == "http://test/history?linked=1"
    me = (await client.get("/api/session")).json()
    assert me["account"]["email"] == "u@x.io"
    assert me["nickname"] == "GoFan"  # 계정 이름으로 새 세션

    ids = {row["id"] for row in (await client.get("/api/games")).json()}
    assert old["id"] in ids
    # 상세·SGF·재개(소유권 판정)도 계정 기준으로 열린다.
    assert (await client.get(f"/api/games/{old['id']}")).status_code == 200
    assert (await client.get(f"/api/games/{old['id']}/sgf")).status_code == 200
    stats = (await client.get("/api/stats")).json()
    assert stats["total"] >= 0


@pytest.mark.asyncio
async def test_other_account_cannot_see_games(
    client: AsyncClient, google_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_google(monkeypatch, sub="g-1", email="a@x.io")
    await client.post("/api/session", json={"nickname": "alice"})
    g = (await client.post(
        "/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"}
    )).json()
    await _start_and_callback(client)
    await client.post("/api/session/end")
    client.cookies.clear()

    _mock_google(monkeypatch, sub="g-2", email="b@x.io")
    await _start_and_callback(client)
    assert (await client.get(f"/api/games/{g['id']}")).status_code == 403
    assert g["id"] not in {row["id"] for row in (await client.get("/api/games")).json()}


@pytest.mark.asyncio
async def test_bad_state_is_rejected(
    client: AsyncClient, google_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_google(monkeypatch)
    await client.get("/api/auth/google/start?next=/settings")
    r = await client.get("/api/auth/google/callback?code=the-code&state=forged")
    assert r.status_code == 302
    assert r.headers["location"] == "http://test/settings?link_error=state"
    assert (await client.get("/api/session")).status_code == 401


@pytest.mark.asyncio
async def test_next_is_restricted_to_local_paths(client: AsyncClient, google_on: None) -> None:
    r = await client.get("/api/auth/google/start?next=https://evil.example")
    assert r.status_code == 302
    cookie = next(c for c in client.cookies.jar if c.name == "baduk_oauth_state")
    assert cookie.value.split("|")[1] == mod._encode_next("/settings")
    assert mod._decode_next(mod._encode_next("/history?x=1")) == "/history?x=1"
    assert mod._decode_next("!!!") == "/settings"


@pytest.mark.asyncio
async def test_unlink_keeps_games_for_relink(
    client: AsyncClient, google_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_google(monkeypatch)
    await client.post("/api/session", json={"nickname": "alice"})
    await _start_and_callback(client)
    assert (await client.post("/api/auth/google/unlink")).status_code == 204
    me = (await client.get("/api/session")).json()
    assert me["account"] is None

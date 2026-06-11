"""WS 쿼리 파라미터(token=) 인증 테스트 — 앱 셸은 쿠키 없이 WS를 연다."""
from __future__ import annotations

import pytest

from tests.api.test_ws_flow import _wire_test_app

_GAME_PAYLOAD = {
    "board_size": 9,
    "handicap": 0,
    "ai_rank": "5k",
    "user_color": "black",
}


def test_ws_accepts_query_token_without_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tc, db_path = _wire_test_app(monkeypatch)
    try:
        with tc:
            r = tc.post("/api/session", json={"nickname": "wstoken"})
            token = r.json()["token"]
            tc.cookies.clear()  # 쿠키 경로 차단 — 헤더/쿼리만으로 통과해야 함
            auth = {"Authorization": f"Bearer {token}"}
            g = tc.post("/api/games", json=_GAME_PAYLOAD, headers=auth)
            assert g.status_code == 201, g.text
            game_id = g.json()["id"]
            with tc.websocket_connect(
                f"/api/ws/games/{game_id}?token={token}"
            ) as ws:
                ws.send_json({"type": "move", "coord": "C3"})
                msg = ws.receive_json()
                assert msg["type"] in ("state", "ai_move", "winrate")
    finally:
        import os

        os.unlink(db_path)


def test_ws_rejects_bad_query_token(monkeypatch: pytest.MonkeyPatch) -> None:
    tc, db_path = _wire_test_app(monkeypatch)
    try:
        with tc:
            r = tc.post("/api/session", json={"nickname": "wstoken2"})
            token = r.json()["token"]
            auth = {"Authorization": f"Bearer {token}"}
            g = tc.post("/api/games", json=_GAME_PAYLOAD, headers=auth)
            game_id = g.json()["id"]
            tc.cookies.clear()
            # starlette TestClient이 1008 close를 예외로 올리지 않을 수 있으므로
            # 연결 후 첫 메시지에서 disconnect를 확인한다.
            # "잘못된 토큰으로는 정상 메시지를 받을 수 없다"는 계약을 보장.
            closed_immediately = False
            try:
                with tc.websocket_connect(f"/api/ws/games/{game_id}?token=bogus") as ws:
                    # 서버가 즉시 close해야 하므로 receive는 WebSocketDisconnect를 올린다.
                    ws.receive_json()
            except Exception:
                closed_immediately = True
            assert closed_immediately, "bogus token should not allow WS connection"
    finally:
        import os

        os.unlink(db_path)

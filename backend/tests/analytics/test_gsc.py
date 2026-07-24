# GSC 응답 파서 검증(순수 함수). HTTP·인증은 통합 범위 밖.
from __future__ import annotations

from app.core.search_console.gsc import parse_gsc_response


def test_parse_gsc_response():
    payload = {"rows": [
        {"keys": ["바둑 단수 뜻", "https://inkbaduk.com/glossary/dansu", "2026-07-20"],
         "clicks": 0, "impressions": 36, "ctr": 0.0, "position": 13.2},
    ]}
    rows = parse_gsc_response(payload)
    assert len(rows) == 1
    assert rows[0].query == "바둑 단수 뜻"
    assert rows[0].page == "https://inkbaduk.com/glossary/dansu"
    assert rows[0].impressions == 36
    assert rows[0].date == "2026-07-20"


def test_parse_gsc_response_empty():
    assert parse_gsc_response({}) == []

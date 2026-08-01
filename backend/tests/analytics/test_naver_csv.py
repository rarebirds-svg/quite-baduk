# 네이버 검색어 CSV 파서 검증.
from __future__ import annotations

from app.core.search_console.naver_csv import parse_naver_csv

CSV = "﻿검색어,클릭,노출,CTR(%)\n바둑 단수 뜻,0,36,0\n계가,0,5,0\n"


def test_parse_naver_csv():
    rows = parse_naver_csv(CSV)
    assert len(rows) == 2
    assert rows[0].query == "바둑 단수 뜻"
    assert rows[0].impressions == 36
    assert rows[0].clicks == 0


def test_parse_naver_csv_skips_blank():
    rows = parse_naver_csv("검색어,클릭,노출,CTR(%)\n\n,,,\n")
    assert rows == []

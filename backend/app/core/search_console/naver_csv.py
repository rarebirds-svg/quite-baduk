# 네이버 서치어드바이저 '검색 키워드' CSV export를 파싱한다(검색어·클릭·노출·CTR).
from __future__ import annotations

import csv
import io

from pydantic import BaseModel


class NaverRow(BaseModel):
    query: str
    clicks: int
    impressions: int
    ctr: float


def _num(value: str) -> float:
    try:
        return float(value.replace(",", "").replace("%", "").strip())
    except ValueError:
        return 0.0


def parse_naver_csv(text: str) -> list[NaverRow]:
    text = text.lstrip("﻿")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    out: list[NaverRow] = []
    for r in rows[1:]:  # 헤더 스킵
        if len(r) < 3 or not r[0].strip():
            continue
        out.append(NaverRow(
            query=r[0].strip(),
            clicks=int(_num(r[1])),
            impressions=int(_num(r[2])),
            ctr=_num(r[3]) if len(r) > 3 else 0.0,
        ))
    return out

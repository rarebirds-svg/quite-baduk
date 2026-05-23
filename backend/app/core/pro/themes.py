# 프로기보 테마 카탈로그 — slug → 필터 SQLAlchemy clause 매핑.
"""테마 카탈로그.

각 테마는 정적 dict로 정의된다. slug는 URL·canonical에 쓰이므로 변경 금지.
filter_type별로 ProGame 컬럼에 대한 SQLAlchemy 표현식을 반환한다.
"""
from __future__ import annotations

from typing import Any, cast

from sqlalchemy.sql import ColumnElement

from app.models import ProGame

THEMES: list[dict[str, Any]] = [
    {
        "slug": "masterpieces",
        "label": "명국선",
        "description": "도사쿠·슈사쿠 등 옛 명인의 명국 모음.",
        "filter_type": "collection",
        "filter_value": "masterpiece",
    },
    {
        "slug": "world-finals",
        "label": "세계기전 결승",
        "description": "응씨배·잉씨배·LG·삼성·춘란 등 세계기전 결승국.",
        "filter_type": "collection",
        "filter_value": "world",
    },
    {
        "slug": "cwi",
        "label": "CWI 공개기보",
        "description": "Centrum Wiskunde & Informatica 퍼블릭 도메인 컬렉션.",
        "filter_type": "collection",
        "filter_value": "cwi",
    },
    {
        "slug": "honinbo",
        "label": "본인방전",
        "description": "일본 본인방전 관련 기보.",
        "filter_type": "event_like",
        "filter_value": "Honinbo",
    },
    {
        "slug": "castle-games",
        "label": "오성 (御城碁)",
        "description": "에도 시대 오성기보.",
        "filter_type": "event_exact",
        "filter_value": "Castle Game",
    },
    {
        "slug": "21st-century",
        "label": "21세기 명국",
        "description": "2000년 이후 대국.",
        "filter_type": "date_gte",
        "filter_value": "2000-01-01",
    },
]


def theme_by_slug(slug: str) -> dict[str, Any] | None:
    return next((t for t in THEMES if t["slug"] == slug), None)


def theme_query_clause(slug: str) -> ColumnElement[bool] | None:
    """slug에 해당하는 SQLAlchemy WHERE clause. 모르는 slug는 None."""
    theme = theme_by_slug(slug)
    if theme is None:
        return None
    ft = theme["filter_type"]
    fv = theme["filter_value"]
    if ft == "collection":
        return cast(ColumnElement[bool], ProGame.collection == fv)
    if ft == "event_like":
        return cast(ColumnElement[bool], ProGame.event.like(f"%{fv}%"))
    if ft == "event_exact":
        return cast(ColumnElement[bool], ProGame.event == fv)
    if ft == "date_gte":
        return cast(ColumnElement[bool], ProGame.game_date >= fv)
    raise ValueError(f"unknown filter_type: {ft}")

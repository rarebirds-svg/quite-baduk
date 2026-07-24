# 구글 Search Console Search Analytics API 클라이언트 — 서비스 계정으로 검색어 통계를 가져온다.
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from app.config import settings

_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


class GscRow(BaseModel):
    query: str
    page: str | None
    clicks: int
    impressions: int
    ctr: float
    position: float
    date: str


def parse_gsc_response(payload: dict[str, Any]) -> list[GscRow]:
    out: list[GscRow] = []
    for r in payload.get("rows", []):
        keys = r.get("keys", [])
        out.append(GscRow(
            query=keys[0] if len(keys) > 0 else "",
            page=keys[1] if len(keys) > 1 else None,
            date=keys[2] if len(keys) > 2 else "",
            clicks=int(r.get("clicks", 0)),
            impressions=int(r.get("impressions", 0)),
            ctr=float(r.get("ctr", 0.0)),
            position=float(r.get("position", 0.0)),
        ))
    return out


def _access_token() -> str | None:
    if not settings.gsc_service_account_json:
        return None
    # google-auth로 서비스 계정 토큰 발급.
    from google.auth.transport.requests import Request as GAuthRequest
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
        settings.gsc_service_account_json, scopes=[_SCOPE]
    )  # google-auth는 타입 스텁 미제공
    creds.refresh(GAuthRequest())
    return str(creds.token)


async def fetch_search_analytics(start: str, end: str) -> list[GscRow]:
    """지정 기간의 검색어·페이지·날짜별 통계. 설정 없으면 빈 리스트."""
    token = _access_token()
    if not token or not settings.gsc_property_url:
        return []
    url = (
        "https://searchconsole.googleapis.com/webmasters/v3/sites/"
        f"{quote(settings.gsc_property_url, safe='')}/searchAnalytics/query"
    )
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["query", "page", "date"],
        "rowLimit": 5000,
    }
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(url, json=body, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        return parse_gsc_response(resp.json())

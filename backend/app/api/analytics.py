# 익명 방문 비콘 수집 엔드포인트 — 봇 제외 후 국가·해시를 붙여 visit_hits에 적재한다.
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app.client_ip import client_country, client_ip
from app.core.analytics.bots import is_bot
from app.core.analytics.hashing import daily_salt, visitor_hash
from app.core.analytics.referrer import classify_source, parse_referrer_host
from app.deps import DbSession
from app.models.visit_hit import VisitHit

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class HitBody(BaseModel):
    path: str = Field(max_length=512)
    referrer: str = Field(default="", max_length=2048)


def _device(user_agent: str | None) -> str | None:
    if not user_agent:
        return None
    return "mobile" if "mobi" in user_agent.lower() else "desktop"


@router.post("/hit", status_code=204)
async def hit(body: HitBody, request: Request, db: DbSession) -> Response:
    ua = request.headers.get("user-agent")
    if is_bot(ua):
        return Response(status_code=204)
    host = parse_referrer_host(body.referrer)
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    ip = client_ip(request)
    db.add(
        VisitHit(
            path=body.path[:512],
            referrer_host=host,
            source=classify_source(host),
            country=client_country(request),
            visitor_hash=visitor_hash(ip, daily_salt(day)),
            device=_device(ua),
        )
    )
    await db.commit()
    return Response(status_code=204)

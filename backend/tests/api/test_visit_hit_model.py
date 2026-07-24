# visit_hits 모델의 삽입·조회를 검증한다.
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.visit_hit import VisitHit


@pytest.mark.asyncio
async def test_visit_hit_insert(client):  # client 픽스처가 테스트 DB 바인딩
    from app.db import AsyncSessionLocal  # client 픽스처가 리바인딩한 뒤에 임포트해야 함

    async with AsyncSessionLocal() as db:
        db.add(VisitHit(path="/glossary/sahwal", referrer_host="google.com",
                        source="search", country="KR", visitor_hash="abc", device="mobile"))
        await db.commit()
        rows = (await db.execute(select(VisitHit))).scalars().all()
        assert len(rows) == 1
        assert rows[0].source == "search"
        assert rows[0].created_at is not None

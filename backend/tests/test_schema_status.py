"""스키마 리비전 점검 — 마이그레이션 누락(OPS-20260907-01)이 헬스에 드러나야 한다."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schema_status import head_revision, migration_status


def test_head_revision_is_latest_migration_file() -> None:
    assert head_revision() == "0020"


@pytest.mark.asyncio
async def test_status_unknown_without_alembic_table(db_session: AsyncSession) -> None:
    # create_all로 만든 테스트 DB엔 alembic_version이 없다 → 판단 불가(None), 장애 아님.
    st = await migration_status(db_session)
    assert st["current"] is None and st["head"] == "0020" and st["pending"] is None


@pytest.mark.asyncio
async def test_status_pending_when_behind_head(db_session: AsyncSession) -> None:
    await db_session.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))
    await db_session.execute(text("INSERT INTO alembic_version VALUES ('0019')"))
    await db_session.commit()
    st = await migration_status(db_session)
    assert st == {"current": "0019", "head": "0020", "pending": True}
    await db_session.execute(text("UPDATE alembic_version SET version_num='0020'"))
    await db_session.commit()
    assert (await migration_status(db_session))["pending"] is False


@pytest.mark.asyncio
async def test_health_reports_migrations(client: AsyncClient, db_session: AsyncSession) -> None:
    body = (await client.get("/api/health")).json()
    assert body["migrations"]["head"] == "0020"
    assert body["status"] == "ok"  # 판단 불가는 degraded로 내리지 않는다

    await db_session.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))
    await db_session.execute(text("INSERT INTO alembic_version VALUES ('0019')"))
    await db_session.commit()
    body = (await client.get("/api/health")).json()
    assert body["migrations"] == {"current": "0019", "head": "0020", "pending": True}
    assert body["status"] == "degraded"

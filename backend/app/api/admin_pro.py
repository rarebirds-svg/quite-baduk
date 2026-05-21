# 프로 기보 관리자 API — 최근 기보 SGF 업로드·목록·삭제 (관리자 전용)
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete as _sa_delete
from sqlalchemy import select

from app.core.sgf.import_sgf import InvalidProSgf, parse_pro_sgf
from app.deps import AdminSession, DbSession
from app.models import ProGame

router = APIRouter(prefix="/api/admin/pro-games", tags=["admin"])


class UploadResult(BaseModel):
    inserted: int
    skipped: int
    failed: list[str]


class AdminProRow(BaseModel):
    id: int
    collection: str
    black_player: str
    white_player: str
    event: str | None
    game_date: date | None
    result: str | None
    move_count: int
    source_note: str | None


class AdminProList(BaseModel):
    rows: list[AdminProRow]


@router.post("", response_model=UploadResult)
async def upload_pro_games(
    _: AdminSession,
    db: DbSession,
    files: list[UploadFile],
) -> UploadResult:
    """SGF 파일을 파싱·정제해 'recent' 컬렉션으로 적재. content_hash가
    이미 있으면 스킵, 파싱 실패 파일은 failed에 모은다."""
    inserted = 0
    skipped = 0
    failed: list[str] = []
    seen: set[str] = set()
    for f in files:
        raw = (await f.read()).decode("utf-8", errors="replace")
        try:
            parsed = parse_pro_sgf(raw)
        except InvalidProSgf:
            failed.append(f.filename or "(unnamed)")
            continue
        dup = (
            await db.execute(
                select(ProGame.id).where(
                    ProGame.content_hash == parsed.content_hash
                )
            )
        ).scalar_one_or_none()
        if parsed.content_hash in seen or dup is not None:
            skipped += 1
            continue
        db.add(ProGame.from_parsed(parsed, collection="recent"))
        seen.add(parsed.content_hash)
        inserted += 1
    await db.commit()
    return UploadResult(inserted=inserted, skipped=skipped, failed=failed)


@router.get("", response_model=AdminProList)
async def list_pro_games(_: AdminSession, db: DbSession) -> AdminProList:
    """관리자 관리 화면용 전체 목록 (최근 등록 순)."""
    games = (
        await db.execute(select(ProGame).order_by(ProGame.id.desc()))
    ).scalars().all()
    return AdminProList(
        rows=[AdminProRow.model_validate(g, from_attributes=True) for g in games]
    )


@router.delete("/{game_id}")
async def delete_pro_game(
    game_id: int,
    _: AdminSession,
    db: DbSession,
) -> dict[str, bool]:
    res = await db.execute(_sa_delete(ProGame).where(ProGame.id == game_id))
    await db.commit()
    if getattr(res, "rowcount", 0) == 0:
        raise HTTPException(status_code=404, detail="pro_game_not_found")
    return {"deleted": True}

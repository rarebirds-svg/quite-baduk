# 프로 기보(pro_games) 테이블 ORM 모델 — 정제 SGF와 대국 메타를 보관한다.
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.sgf.import_sgf import ParsedProGame
from app.db import Base


class ProGame(Base):
    __tablename__ = "pro_games"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 'masterpiece'(명국선 시드) | 'world'(세계 기전 결승 시드) | 'recent'(관리자 업로드)
    collection: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    black_player: Mapped[str] = mapped_column(String(64), nullable=False)
    white_player: Mapped[str] = mapped_column(String(64), nullable=False)
    black_rank: Mapped[str | None] = mapped_column(String(16), nullable=True)
    white_rank: Mapped[str | None] = mapped_column(String(16), nullable=True)
    event: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # SGF RO 원문 — 결승 제N국 등. 표기 로컬라이즈는 web 계층.
    round: Mapped[str | None] = mapped_column(String(32), nullable=True)
    game_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    result: Mapped[str | None] = mapped_column(String(16), nullable=True)
    board_size: Mapped[int] = mapped_column(Integer, nullable=False)
    handicap: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    komi: Mapped[float] = mapped_column(Float, nullable=False, default=6.5)
    move_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 해설(C[]) 등 마크업을 제거한 정제 SGF 원문.
    sgf: Mapped[str] = mapped_column(Text, nullable=False)
    # 출처 메모 — 관리자만 보는 비공개 필드.
    source_note: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # 정제 SGF의 sha256 — 시드·업로드 중복 적재 방지용 UNIQUE.
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    @classmethod
    def from_parsed(
        cls,
        parsed: ParsedProGame,
        *,
        collection: str,
        source_note: str | None = None,
    ) -> ProGame:
        """파싱 결과를 ORM 행으로 매핑. 업로드·시드 양쪽이 공유한다."""
        return cls(
            collection=collection,
            black_player=parsed.black_player,
            white_player=parsed.white_player,
            black_rank=parsed.black_rank,
            white_rank=parsed.white_rank,
            event=parsed.event,
            round=parsed.round,
            game_date=parsed.game_date,
            result=parsed.result,
            board_size=parsed.board_size,
            handicap=parsed.handicap,
            komi=parsed.komi,
            move_count=parsed.move_count,
            sgf=parsed.clean_sgf,
            source_note=source_note,
            content_hash=parsed.content_hash,
        )

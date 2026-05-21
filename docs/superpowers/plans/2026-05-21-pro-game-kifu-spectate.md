# 프로 기보 관전 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 관전 모드에 퍼블릭 도메인 프로 기보(명국선·최근 기보)를 추가해 사용자가 명국을 재생·감상할 수 있게 한다.

**Architecture:** 신규 `pro_games` 테이블에 해설 제거된 정제 SGF + 메타를 저장하고, 읽을 때 SGF를 수순으로 파싱한다. 명국선은 리포 시드 SGF를 멱등 스크립트로 적재, 최근 기보는 관리자 SGF 업로드로 추가한다. `/spectate` 페이지를 탭으로 나눠 잉크바둑 대국과 프로 기보를 분리한다.

**Tech Stack:** FastAPI · SQLAlchemy 2 async · SQLite · Alembic · sgfmill (SGF 파서) · Next.js 14 · TypeScript · Tailwind

설계서: `docs/superpowers/specs/2026-05-21-pro-game-kifu-spectate-design.md`

---

## File Structure

| 파일 | 책임 | 신규/수정 |
|---|---|---|
| `backend/pyproject.toml` | sgfmill 의존성 추가 | 수정 |
| `backend/app/models/pro_game.py` | `pro_games` 테이블 ORM + `from_parsed` 매퍼 | 신규 |
| `backend/app/models/__init__.py` | ProGame export | 수정 |
| `backend/migrations/versions/0013_pro_games.py` | `pro_games` 테이블 생성 | 신규 |
| `backend/app/core/sgf/__init__.py` | 패키지 마커 (빈 파일) | 신규 |
| `backend/app/core/sgf/import_sgf.py` | SGF 파싱·정제·메타 추출 (DB 비의존 순수 모듈) | 신규 |
| `backend/app/api/spectate_pro.py` | 프로 기보 공개 조회 API | 신규 |
| `backend/app/api/admin_pro.py` | 최근 기보 업로드·관리 API (관리자 전용) | 신규 |
| `backend/app/main.py` | 신규 라우터 등록 | 수정 |
| `backend/scripts/seed_pro_games.py` | 명국선 SGF 멱등 적재 스크립트 | 신규 |
| `backend/data/pro_games/masterpieces/README.md` | 명국선 SGF 배치 안내 | 신규 |
| `backend/tests/core/test_sgf_import.py` | SGF 파서 테스트 | 신규 |
| `backend/tests/api/test_spectate_pro.py` | 공개 조회 API 테스트 | 신규 |
| `backend/tests/api/test_admin_pro.py` | 관리자 API 테스트 | 신규 |
| `web/lib/board.ts` | `replay()` 공유 함수 추가 | 수정 |
| `web/app/spectate/[id]/page.tsx` | 로컬 `replay()` 제거, board.ts에서 import | 수정 |
| `web/app/spectate/page.tsx` | 탭(잉크바둑/프로 기보) 분리 | 수정 |
| `web/app/spectate/pro/[id]/page.tsx` | 프로 기보 재생 페이지 | 신규 |
| `web/app/admin/pro-games/page.tsx` | 관리자 프로 기보 업로드·관리 화면 | 신규 |
| `web/lib/i18n/ko.json`, `en.json` | 신규 문구 | 수정 |

---

## Task 1: sgfmill 의존성 추가

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: pyproject.toml 의존성에 sgfmill 추가**

`dependencies` 목록의 `"greenlet>=3.0",` 다음 줄에 추가:

```toml
  "greenlet>=3.0",
  "sgfmill>=1.1.1",
```

- [ ] **Step 2: 설치**

Run: `cd backend && source .venv311/bin/activate && pip install -e ".[dev]"`
Expected: `Successfully installed sgfmill-...`

- [ ] **Step 3: import 확인**

Run: `cd backend && source .venv311/bin/activate && python -c "from sgfmill import sgf; print(sgf.Sgf_game(size=19).get_size())"`
Expected: `19`

- [ ] **Step 4: Commit**

```bash
cd backend && git add pyproject.toml && git commit -m "build: add sgfmill SGF parser dependency"
```

---

## Task 2: ProGame 모델

**Files:**
- Create: `backend/app/models/pro_game.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 모델 파일 작성**

`backend/app/models/pro_game.py`:

```python
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
    # 'masterpiece'(명국선 시드) | 'recent'(관리자 업로드)
    collection: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    black_player: Mapped[str] = mapped_column(String(64), nullable=False)
    white_player: Mapped[str] = mapped_column(String(64), nullable=False)
    black_rank: Mapped[str | None] = mapped_column(String(16), nullable=True)
    white_rank: Mapped[str | None] = mapped_column(String(16), nullable=True)
    event: Mapped[str | None] = mapped_column(String(128), nullable=True)
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
```

> 이 모델은 Task 4의 `ParsedProGame` 데이터클래스에 의존한다. Task 4를 먼저 끝내거나, 이 단계에서 import 에러가 나면 Task 4 완료 후 다시 확인한다.

- [ ] **Step 2: models/__init__.py 에 등록**

`backend/app/models/__init__.py` 전체를 다음으로 교체:

```python
from app.models.analysis_cache import AnalysisCache
from app.models.game import Game
from app.models.move import Move
from app.models.pro_game import ProGame
from app.models.session import Session
from app.models.session_history import SessionHistory

__all__ = [
    "Session",
    "Game",
    "Move",
    "AnalysisCache",
    "SessionHistory",
    "ProGame",
]
```

- [ ] **Step 3: Commit** (Task 4 완료 후 import 검증되면 함께 커밋 가능 — 우선 커밋해도 무방)

```bash
cd backend && git add app/models/pro_game.py app/models/__init__.py && git commit -m "feat(model): add ProGame table for pro-game kifu"
```

---

## Task 3: Alembic 마이그레이션 0013

**Files:**
- Create: `backend/migrations/versions/0013_pro_games.py`

- [ ] **Step 1: 마이그레이션 파일 작성**

`backend/migrations/versions/0013_pro_games.py`:

```python
# 프로 기보(pro_games) 테이블을 생성하는 마이그레이션
"""Create the pro_games table for spectatable professional game records.

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-21

Stores public-domain professional game records (move sequences only, no
commentary) for the spectate area. ``content_hash`` is UNIQUE so the seed
script and admin upload can dedup. No moves table — moves are parsed from
``sgf`` on read.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pro_games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("collection", sa.String(length=16), nullable=False),
        sa.Column("black_player", sa.String(length=64), nullable=False),
        sa.Column("white_player", sa.String(length=64), nullable=False),
        sa.Column("black_rank", sa.String(length=16), nullable=True),
        sa.Column("white_rank", sa.String(length=16), nullable=True),
        sa.Column("event", sa.String(length=128), nullable=True),
        sa.Column("game_date", sa.Date(), nullable=True),
        sa.Column("result", sa.String(length=16), nullable=True),
        sa.Column("board_size", sa.Integer(), nullable=False),
        sa.Column("handicap", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("komi", sa.Float(), nullable=False, server_default="6.5"),
        sa.Column("move_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sgf", sa.Text(), nullable=False),
        sa.Column("source_note", sa.String(length=256), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_pro_games_collection", "pro_games", ["collection"])
    op.create_unique_constraint(
        "uq_pro_games_content_hash", "pro_games", ["content_hash"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_pro_games_content_hash", "pro_games", type_="unique")
    op.drop_index("ix_pro_games_collection", table_name="pro_games")
    op.drop_table("pro_games")
```

- [ ] **Step 2: 마이그레이션 적용**

Run: `cd backend && source .venv311/bin/activate && alembic upgrade head`
Expected: `Running upgrade 0012 -> 0013, Create the pro_games table...`

- [ ] **Step 3: 테이블 확인**

Run: `cd backend && source .venv311/bin/activate && python -c "import sqlite3,os; p=os.environ.get('DB_PATH','app.db'); c=sqlite3.connect(p); print([r[1] for r in c.execute('PRAGMA table_info(pro_games)')])"`
Expected: `['id', 'collection', 'black_player', ...]` 컬럼 목록 출력

- [ ] **Step 4: Commit**

```bash
cd backend && git add migrations/versions/0013_pro_games.py && git commit -m "feat(db): migration 0013 — pro_games table"
```

---

## Task 4: SGF import 모듈

**Files:**
- Create: `backend/app/core/sgf/__init__.py`
- Create: `backend/app/core/sgf/import_sgf.py`
- Test: `backend/tests/core/test_sgf_import.py`

- [ ] **Step 1: 패키지 마커 생성**

`backend/app/core/sgf/__init__.py` — 빈 파일 (CLAUDE.md 규칙 6 예외: 빈 패키지 마커).

```python
```

- [ ] **Step 2: 실패하는 테스트 작성**

`backend/tests/core/test_sgf_import.py`:

```python
# SGF import 모듈(파싱·정제·메타 추출) 단위 테스트
from __future__ import annotations

from datetime import date

import pytest

from app.core.sgf.import_sgf import InvalidProSgf, parse_pro_sgf

_GAME = (
    "(;GM[1]FF[4]CA[UTF-8]SZ[19]KM[6.5]"
    "PB[Test Black]PW[Test White]BR[9p]WR[9p]"
    "EV[Test Cup]DT[2026-01-15]RE[B+R]"
    ";B[pd];W[dp];B[pp]C[good move];W[dd])"
)
_WITH_VARIATION = "(;GM[1]SZ[19];B[pd];W[dp](;B[pp])(;B[dd]))"


def test_parse_extracts_metadata() -> None:
    parsed = parse_pro_sgf(_GAME)
    assert parsed.black_player == "Test Black"
    assert parsed.white_player == "Test White"
    assert parsed.black_rank == "9p"
    assert parsed.event == "Test Cup"
    assert parsed.game_date == date(2026, 1, 15)
    assert parsed.result == "B+R"
    assert parsed.board_size == 19
    assert parsed.move_count == 4


def test_parse_produces_gtp_coords() -> None:
    parsed = parse_pro_sgf(_GAME)
    first = parsed.moves[0]
    assert first.move_number == 1
    assert first.color == "B"
    # SGF [pd] = col 15, row 15 (0-indexed from bottom) -> GTP Q16
    assert first.coord == "Q16"


def test_clean_sgf_strips_comments() -> None:
    parsed = parse_pro_sgf(_GAME)
    assert "C[good move]" not in parsed.clean_sgf
    assert "good move" not in parsed.clean_sgf


def test_variations_ignored_main_line_only() -> None:
    parsed = parse_pro_sgf(_WITH_VARIATION)
    # root + B[pd] + W[dp] + B[pp] (first variation) = 3 moves
    assert parsed.move_count == 3


def test_content_hash_is_stable() -> None:
    a = parse_pro_sgf(_GAME)
    b = parse_pro_sgf(_GAME)
    assert a.content_hash == b.content_hash
    assert len(a.content_hash) == 64


def test_empty_sgf_rejected() -> None:
    with pytest.raises(InvalidProSgf):
        parse_pro_sgf("(;GM[1]SZ[19])")


def test_bad_board_size_rejected() -> None:
    with pytest.raises(InvalidProSgf):
        parse_pro_sgf("(;GM[1]SZ[12];B[aa])")


def test_garbage_input_rejected() -> None:
    with pytest.raises(InvalidProSgf):
        parse_pro_sgf("this is not sgf at all")
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd backend && source .venv311/bin/activate && pytest tests/core/test_sgf_import.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.core.sgf.import_sgf'`

- [ ] **Step 4: import_sgf.py 구현**

`backend/app/core/sgf/import_sgf.py`:

```python
# SGF 파싱·정제·메타 추출 — 프로 기보를 본선 수순만 남긴 정제 SGF로 변환한다.
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date

from sgfmill import sgf

# GTP 열 문자 — 'I'를 건너뛴다.
_GTP_COLS = "ABCDEFGHJKLMNOPQRST"
_VALID_SIZES = {9, 13, 19}


class InvalidProSgf(ValueError):
    """SGF를 프로 기보로 적재할 수 없을 때 발생."""


@dataclass(frozen=True)
class ProMove:
    move_number: int
    color: str  # 'B' | 'W'
    coord: str | None  # GTP 좌표, 패스는 None


@dataclass(frozen=True)
class ParsedProGame:
    black_player: str
    white_player: str
    black_rank: str | None
    white_rank: str | None
    event: str | None
    game_date: date | None
    result: str | None
    board_size: int
    handicap: int
    komi: float
    move_count: int
    clean_sgf: str
    content_hash: str
    moves: list[ProMove]


def _point_to_gtp(point: tuple[int, int] | None) -> str | None:
    if point is None:
        return None
    row, col = point
    return f"{_GTP_COLS[col]}{row + 1}"


def _parse_dt(dt: str | None) -> date | None:
    if not dt:
        return None
    head = dt.split(",")[0].strip()
    try:
        return date.fromisoformat(head)
    except ValueError:
        return None


def _build_clean_sgf(
    *,
    size: int,
    komi: float,
    handicap: int,
    setup_black: list[tuple[int, int]],
    moves: list[tuple[str, tuple[int, int] | None]],
    meta: dict[str, str | None],
) -> bytes:
    """본선 수순과 화이트리스트 메타만 담은 새 SGF를 직렬화한다.
    변화도·해설은 새로 만든 게임 객체엔 애초에 들어가지 않는다."""
    g = sgf.Sgf_game(size=size)
    g.set_komi(komi)
    root = g.get_root()
    for ident, val in meta.items():
        if val:
            root.set(ident, val)
    if handicap:
        root.set("HA", handicap)
    if setup_black:
        root.set("AB", setup_black)
    for color, point in moves:
        node = g.extend_main_sequence()
        node.set_move(color, point)
    return g.serialise()


def parse_pro_sgf(sgf_text: str) -> ParsedProGame:
    """SGF 텍스트를 파싱해 정제·메타·수순을 담은 ParsedProGame을 반환.
    적재 불가능한 입력은 InvalidProSgf를 던진다."""
    try:
        game = sgf.Sgf_game.from_bytes(sgf_text.encode("utf-8"))
    except ValueError as e:
        raise InvalidProSgf(f"SGF 파싱 실패: {e}") from e

    size = game.get_size()
    if size not in _VALID_SIZES:
        raise InvalidProSgf(f"지원하지 않는 판 크기: {size}")

    root = game.get_root()

    def _opt(ident: str) -> str | None:
        if root.has_property(ident):
            text = str(root.get(ident)).strip()
            return text or None
        return None

    black_player = _opt("PB") or "흑"
    white_player = _opt("PW") or "백"
    dt_raw = _opt("DT")

    try:
        komi = game.get_komi()
    except ValueError:
        komi = 6.5
    handicap = game.get_handicap() or 0

    raw_moves: list[tuple[str, tuple[int, int] | None]] = []
    for node in game.get_main_sequence():
        color, point = node.get_move()
        if color is None:
            continue
        raw_moves.append((color, point))
    if not raw_moves:
        raise InvalidProSgf("착수가 없는 SGF")

    setup_black, _white, _empty = root.get_setup_stones()

    clean_bytes = _build_clean_sgf(
        size=size,
        komi=komi,
        handicap=handicap,
        setup_black=sorted(setup_black),
        moves=raw_moves,
        meta={
            "PB": black_player,
            "PW": white_player,
            "BR": _opt("BR"),
            "WR": _opt("WR"),
            "EV": _opt("EV"),
            "DT": dt_raw,
            "RE": _opt("RE"),
        },
    )
    clean_sgf = clean_bytes.decode("utf-8")

    moves = [
        ProMove(
            move_number=i + 1,
            color=color.upper(),
            coord=_point_to_gtp(point),
        )
        for i, (color, point) in enumerate(raw_moves)
    ]

    return ParsedProGame(
        black_player=black_player,
        white_player=white_player,
        black_rank=_opt("BR"),
        white_rank=_opt("WR"),
        event=_opt("EV"),
        game_date=_parse_dt(dt_raw),
        result=_opt("RE"),
        board_size=size,
        handicap=handicap,
        komi=komi,
        move_count=len(moves),
        clean_sgf=clean_sgf,
        content_hash=hashlib.sha256(clean_bytes).hexdigest(),
        moves=moves,
    )
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd backend && source .venv311/bin/activate && pytest tests/core/test_sgf_import.py -q`
Expected: PASS — 8 passed

- [ ] **Step 6: lint·type 확인**

Run: `cd backend && source .venv311/bin/activate && ruff check app/core/sgf/ && mypy app/core/sgf/`
Expected: `All checks passed!` / `Success: no issues found`

> mypy가 sgfmill에 타입 스텁이 없다고 경고하면, `import_sgf.py`의 sgfmill import 줄에 `# type: ignore[import-untyped]` 를 사유 주석과 함께 붙인다: `from sgfmill import sgf  # type: ignore[import-untyped]  # sgfmill 타입 스텁 없음`

- [ ] **Step 7: Commit**

```bash
cd backend && git add app/core/sgf/ tests/core/test_sgf_import.py && git commit -m "feat(sgf): add SGF import module — parse, clean, extract metadata"
```

---

## Task 5: 프로 기보 공개 조회 API

**Files:**
- Create: `backend/app/api/spectate_pro.py`
- Test: `backend/tests/api/test_spectate_pro.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/api/test_spectate_pro.py`:

```python
# 프로 기보 공개 조회 API(/api/spectate/pro) 계약 테스트
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.sgf.import_sgf import parse_pro_sgf
from app.models import ProGame

_SGF = (
    "(;GM[1]FF[4]SZ[19]KM[6.5]PB[Lee]PW[Cho]BR[9p]WR[9p]"
    "EV[Demo Cup]DT[2026-02-01]RE[W+2.5];B[pd];W[dp];B[pp];W[dd])"
)


async def _signup(client: AsyncClient, nickname: str) -> None:
    r = await client.post("/api/session", json={"nickname": nickname})
    assert r.status_code == 201, r.text


async def _insert_pro_game(db_session, collection: str = "masterpiece") -> int:
    parsed = parse_pro_sgf(_SGF)
    g = ProGame.from_parsed(parsed, collection=collection)
    db_session.add(g)
    await db_session.commit()
    await db_session.refresh(g)
    return g.id


@pytest.mark.asyncio
async def test_pro_list_requires_session(client: AsyncClient) -> None:
    fresh = AsyncClient(transport=client._transport, base_url=client.base_url)
    try:
        r = await fresh.get("/api/spectate/pro")
        assert r.status_code == 401
    finally:
        await fresh.aclose()


@pytest.mark.asyncio
async def test_pro_list_returns_inserted_game(
    client: AsyncClient, db_session
) -> None:
    gid = await _insert_pro_game(db_session)
    await _signup(client, "watcher")
    r = await client.get("/api/spectate/pro")
    assert r.status_code == 200
    rows = r.json()["rows"]
    row = next((x for x in rows if x["id"] == gid), None)
    assert row is not None
    assert row["black_player"] == "Lee"
    assert row["collection"] == "masterpiece"
    assert row["move_count"] == 4


@pytest.mark.asyncio
async def test_pro_list_collection_filter(
    client: AsyncClient, db_session
) -> None:
    mid = await _insert_pro_game(db_session, "masterpiece")
    await _signup(client, "watcher")
    r = await client.get("/api/spectate/pro", params={"collection": "recent"})
    ids = {x["id"] for x in r.json()["rows"]}
    assert mid not in ids


@pytest.mark.asyncio
async def test_pro_detail_returns_moves(
    client: AsyncClient, db_session
) -> None:
    gid = await _insert_pro_game(db_session)
    await _signup(client, "watcher")
    r = await client.get(f"/api/spectate/pro/{gid}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == gid
    assert len(body["moves"]) == 4
    assert body["moves"][0]["coord"] == "Q16"


@pytest.mark.asyncio
async def test_pro_detail_unknown_id_404(client: AsyncClient) -> None:
    await _signup(client, "watcher")
    r = await client.get("/api/spectate/pro/999999")
    assert r.status_code == 404
```

> `db_session`·`client` fixture는 `tests/conftest.py`에 이미 있다. 두 fixture는 같은 임시 DB 파일을 공유하므로 `db_session`으로 삽입한 행이 `client` 요청에서 보인다.

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && source .venv311/bin/activate && pytest tests/api/test_spectate_pro.py -q`
Expected: FAIL — 404 (라우터 미등록)

- [ ] **Step 3: spectate_pro.py 구현**

`backend/app/api/spectate_pro.py`:

```python
# 프로 기보 공개 관전 API — 명국선·최근 기보 목록과 수순 상세를 제공한다.
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_, select

from app.core.sgf.import_sgf import parse_pro_sgf
from app.deps import CurrentSession, DbSession
from app.models import ProGame

router = APIRouter(prefix="/api/spectate/pro", tags=["spectate"])


class ProGameRow(BaseModel):
    id: int
    collection: str
    black_player: str
    white_player: str
    black_rank: str | None
    white_rank: str | None
    event: str | None
    game_date: date | None
    result: str | None
    board_size: int
    handicap: int
    move_count: int


class ProGameList(BaseModel):
    rows: list[ProGameRow]


class ProMoveOut(BaseModel):
    move_number: int
    color: str
    coord: str | None


class ProGameDetail(ProGameRow):
    komi: float
    moves: list[ProMoveOut]


@router.get("", response_model=ProGameList)
async def list_pro_games(
    _: CurrentSession,
    db: DbSession,
    collection: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
) -> ProGameList:
    """프로 기보 목록. 닉네임 세션 필요. 최신 대국일 순."""
    stmt = select(ProGame).order_by(
        ProGame.game_date.desc().nullslast(), ProGame.id.desc()
    )
    if collection in ("masterpiece", "recent"):
        stmt = stmt.where(ProGame.collection == collection)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                ProGame.black_player.ilike(like),
                ProGame.white_player.ilike(like),
                ProGame.event.ilike(like),
            )
        )
    stmt = stmt.limit(limit)
    games = (await db.execute(stmt)).scalars().all()
    return ProGameList(
        rows=[ProGameRow.model_validate(g, from_attributes=True) for g in games]
    )


@router.get("/{game_id}", response_model=ProGameDetail)
async def get_pro_game(
    game_id: int,
    _: CurrentSession,
    db: DbSession,
) -> ProGameDetail:
    """프로 기보 상세 — 저장된 SGF를 수순으로 파싱해 함께 반환한다."""
    game = (
        await db.execute(select(ProGame).where(ProGame.id == game_id))
    ).scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="pro_game_not_found")

    parsed = parse_pro_sgf(game.sgf)
    base = ProGameRow.model_validate(game, from_attributes=True)
    return ProGameDetail(
        **base.model_dump(),
        komi=game.komi,
        moves=[
            ProMoveOut(move_number=m.move_number, color=m.color, coord=m.coord)
            for m in parsed.moves
        ],
    )
```

> 라우터 등록은 Task 7에서 한다. 등록 순서가 중요하다 — 이 라우터를 기존 `spectate` 라우터보다 **먼저** 등록해야 `/api/spectate/pro` 가 `spectate`의 `/{game_id}` 로 흡수되지 않는다.

- [ ] **Step 4: 라우터 임시 등록 후 테스트** — Task 7의 main.py 수정을 먼저 적용하고 이 테스트를 돌린다. (Task 7 완료 후 이 단계 재실행)

Run: `cd backend && source .venv311/bin/activate && pytest tests/api/test_spectate_pro.py -q`
Expected: PASS — 5 passed

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/api/spectate_pro.py tests/api/test_spectate_pro.py && git commit -m "feat(spectate): pro-game public list and detail API"
```

---

## Task 6: 관리자 프로 기보 API

**Files:**
- Create: `backend/app/api/admin_pro.py`
- Test: `backend/tests/api/test_admin_pro.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/api/test_admin_pro.py`:

```python
# 관리자 프로 기보 API(/api/admin/pro-games) 테스트 — 업로드·중복·삭제·게이트
from __future__ import annotations

import pytest
from httpx import AsyncClient

_SGF = (
    "(;GM[1]FF[4]SZ[19]KM[6.5]PB[Shin]PW[Park]BR[9p]WR[9p]"
    "EV[Upload Cup]DT[2026-03-01]RE[B+R];B[pd];W[dp];B[pp];W[dd])"
)


async def _signup(client: AsyncClient, nickname: str) -> None:
    r = await client.post("/api/session", json={"nickname": nickname})
    assert r.status_code == 201, r.text


def _sgf_file(name: str, content: str) -> tuple[str, tuple[str, bytes, str]]:
    return ("files", (name, content.encode("utf-8"), "application/x-go-sgf"))


@pytest.mark.asyncio
async def test_upload_requires_admin(client: AsyncClient) -> None:
    await _signup(client, "normaluser")
    r = await client.post(
        "/api/admin/pro-games", files=[_sgf_file("g.sgf", _SGF)]
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_uploads_and_dedups(client: AsyncClient) -> None:
    await _signup(client, "대공")
    r1 = await client.post(
        "/api/admin/pro-games", files=[_sgf_file("g.sgf", _SGF)]
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["inserted"] == 1

    # 같은 SGF 재업로드 → 중복 스킵.
    r2 = await client.post(
        "/api/admin/pro-games", files=[_sgf_file("g.sgf", _SGF)]
    )
    assert r2.json()["inserted"] == 0
    assert r2.json()["skipped"] == 1


@pytest.mark.asyncio
async def test_admin_upload_rejects_bad_sgf(client: AsyncClient) -> None:
    await _signup(client, "대공")
    r = await client.post(
        "/api/admin/pro-games", files=[_sgf_file("bad.sgf", "not sgf")]
    )
    assert r.status_code == 200
    assert r.json()["inserted"] == 0
    assert "bad.sgf" in r.json()["failed"]


@pytest.mark.asyncio
async def test_admin_lists_and_deletes(client: AsyncClient) -> None:
    await _signup(client, "대공")
    await client.post("/api/admin/pro-games", files=[_sgf_file("g.sgf", _SGF)])

    lst = await client.get("/api/admin/pro-games")
    assert lst.status_code == 200
    rows = lst.json()["rows"]
    assert len(rows) == 1
    gid = rows[0]["id"]

    d = await client.delete(f"/api/admin/pro-games/{gid}")
    assert d.status_code == 200

    lst2 = await client.get("/api/admin/pro-games")
    assert lst2.json()["rows"] == []


@pytest.mark.asyncio
async def test_admin_delete_unknown_404(client: AsyncClient) -> None:
    await _signup(client, "대공")
    r = await client.delete("/api/admin/pro-games/999999")
    assert r.status_code == 404
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && source .venv311/bin/activate && pytest tests/api/test_admin_pro.py -q`
Expected: FAIL — 404 (라우터 미등록)

- [ ] **Step 3: admin_pro.py 구현**

`backend/app/api/admin_pro.py`:

```python
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
        if dup is not None:
            skipped += 1
            continue
        db.add(ProGame.from_parsed(parsed, collection="recent"))
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
```

- [ ] **Step 4: 테스트 통과 확인** — Task 7의 main.py 수정 적용 후 실행.

Run: `cd backend && source .venv311/bin/activate && pytest tests/api/test_admin_pro.py -q`
Expected: PASS — 5 passed

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/api/admin_pro.py tests/api/test_admin_pro.py && git commit -m "feat(admin): pro-game upload, list, delete API"
```

---

## Task 7: 라우터 등록

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: import 추가**

`backend/app/main.py`에서 `from app.api import admin as admin_router` 줄 바로 아래에 추가:

```python
    from app.api import admin as admin_router
    from app.api import admin_pro as admin_pro_router
    from app.api import analysis as analysis_router
```

그리고 `from app.api import spectate as spectate_router` 줄 바로 위에 추가:

```python
    from app.api import spectate_pro as spectate_pro_router
    from app.api import spectate as spectate_router
```

- [ ] **Step 2: include_router 추가**

`app.include_router(spectate_router.router)` 줄을 다음 두 줄로 교체한다. **pro 라우터를 먼저** 등록해야 `/api/spectate/pro` 가 `spectate`의 `/{game_id}` 라우트에 흡수되지 않는다:

```python
    app.include_router(spectate_pro_router.router)
    app.include_router(spectate_router.router)
    app.include_router(admin_pro_router.router)
```

- [ ] **Step 3: Task 5·6 테스트 통과 확인**

Run: `cd backend && source .venv311/bin/activate && pytest tests/api/test_spectate_pro.py tests/api/test_admin_pro.py tests/api/test_spectate.py -q`
Expected: PASS — 모두 통과 (기존 spectate 테스트 회귀 없음 포함)

- [ ] **Step 4: 전체 스위트·lint·type**

Run: `cd backend && source .venv311/bin/activate && pytest -q && ruff check . && mypy app`
Expected: 전체 PASS, `All checks passed!`, `Success`

- [ ] **Step 5: Commit**

```bash
cd backend && git add app/main.py && git commit -m "feat(api): register pro-game spectate and admin routers"
```

---

## Task 8: 명국선 시드 스크립트

**Files:**
- Create: `backend/data/pro_games/masterpieces/README.md`
- Create: `backend/scripts/seed_pro_games.py`

- [ ] **Step 1: 명국선 디렉터리 README 작성**

`backend/data/pro_games/masterpieces/README.md`:

```markdown
# 명국선 SGF

이 디렉터리에 명국선으로 노출할 프로 기보 SGF 파일(`*.sgf`)을 둔다.

## 조건

- **순수 수순 기보만.** 해설(`C[]`)은 적재 시 자동 제거되지만, 출처가
  퍼블릭 도메인인지 확인하는 책임은 등록자에게 있다.
- 권장 메타 프로퍼티: `PB`/`PW`(기사), `BR`/`WR`(단위), `EV`(기전),
  `DT`(대국일 `YYYY-MM-DD`), `RE`(결과), `SZ`, `KM`.

## 적재

```bash
cd backend && source .venv311/bin/activate && python -m scripts.seed_pro_games
```

멱등이다 — 이미 적재된 기보(정제 SGF 해시 동일)는 건너뛴다.
```

- [ ] **Step 2: 시드 스크립트 작성**

`backend/scripts/seed_pro_games.py`:

```python
# 명국선 SGF 시드 — data/pro_games/masterpieces/*.sgf 를 멱등 적재한다.
"""명국선 SGF 일괄 적재 스크립트.

Usage (from backend/):

    python -m scripts.seed_pro_games

data/pro_games/masterpieces/ 의 모든 .sgf 를 파싱·정제해 collection=
'masterpiece' 로 적재한다. content_hash 가 이미 있으면 건너뛴다.
깨진 SGF 는 로그를 남기고 스킵하며 배치는 계속 진행한다.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import structlog
from sqlalchemy import select

from app.core.sgf.import_sgf import InvalidProSgf, parse_pro_sgf
from app.db import AsyncSessionLocal
from app.models import ProGame

log = structlog.get_logger()

SEED_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "pro_games"
    / "masterpieces"
)


async def seed() -> None:
    sgf_files = sorted(SEED_DIR.glob("*.sgf"))
    if not sgf_files:
        log.info("seed_pro_games.empty", dir=str(SEED_DIR))
        return

    inserted = 0
    skipped = 0
    failed = 0
    async with AsyncSessionLocal() as db:
        for path in sgf_files:
            try:
                parsed = parse_pro_sgf(path.read_text(encoding="utf-8"))
            except (InvalidProSgf, OSError, UnicodeDecodeError) as e:
                failed += 1
                log.warning("seed_pro_games.parse_failed", file=path.name, error=str(e))
                continue
            dup = (
                await db.execute(
                    select(ProGame.id).where(
                        ProGame.content_hash == parsed.content_hash
                    )
                )
            ).scalar_one_or_none()
            if dup is not None:
                skipped += 1
                continue
            db.add(ProGame.from_parsed(parsed, collection="masterpiece"))
            inserted += 1
        await db.commit()

    log.info(
        "seed_pro_games.done",
        inserted=inserted,
        skipped=skipped,
        failed=failed,
    )


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 3: 빈 디렉터리에서 스크립트 실행 (멱등·무해 확인)**

Run: `cd backend && source .venv311/bin/activate && python -m scripts.seed_pro_games`
Expected: 로그에 `seed_pro_games.empty` 또는 `seed_pro_games.done inserted=0` — 에러 없이 종료

- [ ] **Step 4: lint**

Run: `cd backend && source .venv311/bin/activate && ruff check scripts/seed_pro_games.py`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
cd backend && git add scripts/seed_pro_games.py data/pro_games/masterpieces/README.md && git commit -m "feat(seed): idempotent masterpiece SGF seed script"
```

---

## Task 9: 프론트엔드 — `replay()` 공유 함수 추출

**Files:**
- Modify: `web/lib/board.ts`
- Modify: `web/app/spectate/[id]/page.tsx`

- [ ] **Step 1: board.ts 에 공유 타입·`replay()` 추가**

`web/lib/board.ts` 맨 끝에 추가:

```typescript
// 관전·재생 화면이 공유하는 수순 항목 — 착수 색·좌표·취소 여부.
export interface ReplayMove {
  color: "B" | "W";
  coord: string | null;
  is_undone: boolean;
}

// upto 수까지 둔 반상 문자열을 만든다. 패스·기권·취소수는 건너뛴다.
export function replay(
  size: number,
  moves: ReplayMove[],
  upto: number,
  handicap = 0,
): string {
  let board = ".".repeat(totalCells(size));
  for (const coord of handicapStonesFor(size, handicap)) {
    const xy = gtpToXy(coord, size);
    if (!xy) continue;
    const cells = board.split("");
    cells[xy[1] * size + xy[0]] = "B";
    board = cells.join("");
  }
  for (let i = 0; i < Math.min(upto, moves.length); i++) {
    const m = moves[i];
    if (m.is_undone || !m.coord || m.coord === "pass" || m.coord === "resign")
      continue;
    const xy = gtpToXy(m.coord, size);
    if (!xy) continue;
    board = applyMoveWithCaptures(board, size, xy[0], xy[1], m.color);
  }
  return board;
}
```

- [ ] **Step 2: 기존 watch 페이지에서 로컬 `replay()` 제거하고 import 로 교체**

`web/app/spectate/[id]/page.tsx`:

import 블록 수정 — `from "@/lib/board"` 의 import 목록에 `replay` 추가:

```typescript
import {
  applyMoveWithCaptures,
  gtpToXy,
  handicapStonesFor,
  replay,
  totalCells,
} from "@/lib/board";
```

그리고 파일 안의 로컬 `function replay(...) { ... }` 정의 블록(45–68행) 전체를 삭제한다. `MoveEntryRaw`는 `replay`의 `ReplayMove`와 구조가 호환되므로 호출부(`replay(game.board_size, game.moves, idx, game.handicap ?? 0)`)는 그대로 둔다.

> 삭제 후 `applyMoveWithCaptures`·`handicapStonesFor`·`totalCells`가 페이지 안에서 더는 직접 쓰이지 않으면 import 목록에서도 제거한다 (CLAUDE.md 규칙 3 — 내 변경이 만든 orphan만 정리). 확인: 삭제 후 `replay`만 board 함수를 쓴다면 import는 `gtpToXy, replay`만 남는다.

- [ ] **Step 3: 타입체크·테스트**

Run: `cd web && npm run type-check && npm test -- --run tests/board.test.ts`
Expected: 타입 에러 없음, board 테스트 PASS

- [ ] **Step 4: Commit**

```bash
cd web && git add lib/board.ts app/spectate/[id]/page.tsx && git commit -m "refactor(spectate): extract shared replay() into lib/board"
```

---

## Task 10: 프론트엔드 — `/spectate` 탭 분리

**Files:**
- Modify: `web/app/spectate/page.tsx`
- Modify: `web/lib/i18n/ko.json`, `web/lib/i18n/en.json`

- [ ] **Step 1: i18n 키 추가**

`web/lib/i18n/ko.json` 의 `spectate` 객체 안에 키 추가:

```json
    "tabInkbaduk": "잉크바둑 대국",
    "tabPro": "프로 기보",
    "proMasterpiece": "명국선",
    "proRecent": "최근 기보",
    "proSearch": "기사·기전 검색",
    "proEmpty": "등록된 프로 기보가 없습니다.",
    "proEvent": "기전",
    "proDate": "대국일"
```

`web/lib/i18n/en.json` 의 `spectate` 객체 안에 동일 키:

```json
    "tabInkbaduk": "Inkbaduk Games",
    "tabPro": "Pro Records",
    "proMasterpiece": "Masterpieces",
    "proRecent": "Recent",
    "proSearch": "Search player or event",
    "proEmpty": "No pro records yet.",
    "proEvent": "Event",
    "proDate": "Date"
```

- [ ] **Step 2: spectate 페이지를 탭 구조로 수정**

`web/app/spectate/page.tsx` 를 다음으로 교체:

```tsx
"use client";
// 관전 목록 — 잉크바둑 대국과 프로 기보를 탭으로 나눠 보여주는 페이지.
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useT, useLocale } from "@/lib/i18n";
import { useAuthStore } from "@/store/authStore";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { formatRank } from "@/components/RankPicker";
import { PLAYER_COUNTRY, type PlayerId } from "@/components/PlayerPicker";
import { CountryFlag } from "@/components/CountryFlag";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { ProGameList } from "@/components/ProGameList";

interface SpectateRow {
  id: number;
  user_nickname: string | null;
  user_rank: string | null;
  user_country: string | null;
  ai_player: string | null;
  ai_rank: string;
  ai_style: string;
  board_size: number;
  handicap: number;
  status: string;
  result: string | null;
  move_count: number;
  started_at: string;
  finished_at: string | null;
  is_live: boolean;
}

const REFRESH_SEC = 10;

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return iso;
  }
}

export default function SpectateListPage() {
  const t = useT();
  const [locale] = useLocale();
  const router = useRouter();
  const { session } = useAuthStore();
  const [rows, setRows] = useState<SpectateRow[] | null>(null);

  useEffect(() => {
    if (!session) {
      router.replace("/");
      return;
    }
    let cancelled = false;
    const poll = async () => {
      try {
        const data = await api<{ rows: SpectateRow[] }>("/api/spectate");
        if (!cancelled) setRows(data.rows);
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) router.replace("/");
      }
    };
    poll();
    const id = setInterval(poll, REFRESH_SEC * 1000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [session, router]);

  if (!session) return null;

  const live = rows?.filter((r) => r.is_live) ?? [];
  const ended = rows?.filter((r) => !r.is_live) ?? [];

  return (
    <div className="space-y-6">
      <Hero title={t("spectate.heading")} subtitle={t("spectate.subtitle")} />

      <Tabs defaultValue="inkbaduk">
        <TabsList>
          <TabsTrigger value="inkbaduk">
            {t("spectate.tabInkbaduk")}
          </TabsTrigger>
          <TabsTrigger value="pro">{t("spectate.tabPro")}</TabsTrigger>
        </TabsList>

        <TabsContent value="inkbaduk" className="space-y-6 pt-4">
          {rows === null ? (
            <p className="text-sm text-ink-faint">…</p>
          ) : rows.length === 0 ? (
            <p className="text-sm text-ink-mute">{t("spectate.empty")}</p>
          ) : (
            <>
              <section>
                <h2 className="font-serif text-xl mb-3 flex items-baseline gap-2">
                  {t("spectate.liveSection")}
                  <span className="font-mono text-xs text-ink-faint tabular-nums">
                    {live.length}
                  </span>
                </h2>
                {live.length === 0 ? (
                  <p className="text-xs text-ink-faint font-sans">
                    {t("spectate.noLive")}
                  </p>
                ) : (
                  <SpectateGrid rows={live} locale={locale} t={t} live />
                )}
              </section>

              <RuleDivider weight="faint" />

              <section>
                <h2 className="font-serif text-xl mb-3 flex items-baseline gap-2">
                  {t("spectate.endedSection")}
                  <span className="font-mono text-xs text-ink-faint tabular-nums">
                    {ended.length}
                  </span>
                </h2>
                {ended.length === 0 ? (
                  <p className="text-xs text-ink-faint font-sans">
                    {t("spectate.noEnded")}
                  </p>
                ) : (
                  <SpectateGrid rows={ended} locale={locale} t={t} live={false} />
                )}
              </section>
            </>
          )}
        </TabsContent>

        <TabsContent value="pro" className="pt-4">
          <ProGameList />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function SpectateGrid({
  rows,
  locale,
  t,
  live,
}: {
  rows: SpectateRow[];
  locale: "ko" | "en";
  t: (key: string) => string;
  live: boolean;
}) {
  return (
    <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
      {rows.map((r) => {
        const blackName = r.user_nickname ?? "—";
        const blackRank = r.user_rank ? formatRank(r.user_rank, locale) : null;
        const aiName = r.ai_player
          ? t(`game.players.${r.ai_player}.name`)
          : formatRank(r.ai_rank, locale);
        const userCountry = r.user_country ?? "KR";
        const aiCountry = r.ai_player
          ? PLAYER_COUNTRY[r.ai_player as PlayerId]
          : null;
        return (
          <li key={r.id}>
            <Link
              href={`/spectate/${r.id}`}
              className="block border border-ink-faint p-3 hover:bg-paper-deep transition-base"
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-sans text-sm text-ink inline-flex items-baseline gap-1.5">
                  <CountryFlag code={userCountry} />
                  <span>
                    {blackName}
                    {blackRank && (
                      <span className="text-ink-faint text-xs"> ({blackRank})</span>
                    )}
                  </span>
                  <span className="text-ink-faint">vs</span>
                  <CountryFlag code={aiCountry} />
                  <span>{aiName}</span>
                </span>
                {live ? (
                  <span className="inline-flex items-center gap-1 font-sans text-[10px] uppercase tracking-label text-moss shrink-0">
                    <span className="w-1.5 h-1.5 rounded-full bg-moss" aria-hidden />
                    {t("spectate.liveBadge")}
                  </span>
                ) : (
                  <span className="font-mono text-xs text-ink-faint shrink-0">
                    {r.result ?? "—"}
                  </span>
                )}
              </div>
              <div className="mt-1 font-mono text-[11px] text-ink-faint tabular-nums flex gap-3">
                <span>{r.board_size}×{r.board_size}</span>
                <span>{r.move_count}{t("spectate.movesSuffix")}</span>
                <span>{fmtTime(r.started_at)}</span>
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
```

- [ ] **Step 3: ProGameList 컴포넌트 작성**

`web/components/ProGameList.tsx` 생성:

```tsx
"use client";
// 프로 기보 목록 — 명국선/최근 토글과 기사·기전 검색을 갖춘 관전 탭 본문.
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Input } from "@/components/ui/input";

interface ProRow {
  id: number;
  collection: string;
  black_player: string;
  white_player: string;
  black_rank: string | null;
  white_rank: string | null;
  event: string | null;
  game_date: string | null;
  result: string | null;
  board_size: number;
  move_count: number;
}

type Collection = "masterpiece" | "recent";

export function ProGameList() {
  const t = useT();
  const [collection, setCollection] = useState<Collection>("masterpiece");
  const [rows, setRows] = useState<ProRow[] | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    let cancelled = false;
    setRows(null);
    api<{ rows: ProRow[] }>(
      `/api/spectate/pro?collection=${collection}`,
    )
      .then((d) => {
        if (!cancelled) setRows(d.rows);
      })
      .catch(() => {
        if (!cancelled) setRows([]);
      });
    return () => {
      cancelled = true;
    };
  }, [collection]);

  const filtered = useMemo(() => {
    if (!rows) return null;
    const needle = q.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter((r) =>
      [r.black_player, r.white_player, r.event ?? ""]
        .join(" ")
        .toLowerCase()
        .includes(needle),
    );
  }, [rows, q]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex border border-ink-faint">
          {(["masterpiece", "recent"] as Collection[]).map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCollection(c)}
              className={
                "px-3 py-1.5 font-sans text-xs uppercase tracking-label transition-base " +
                (collection === c
                  ? "bg-oxblood text-paper"
                  : "text-ink-mute hover:text-ink")
              }
            >
              {c === "masterpiece"
                ? t("spectate.proMasterpiece")
                : t("spectate.proRecent")}
            </button>
          ))}
        </div>
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t("spectate.proSearch")}
          className="max-w-xs"
        />
      </div>

      {filtered === null ? (
        <p className="text-sm text-ink-faint">…</p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-ink-mute">{t("spectate.proEmpty")}</p>
      ) : (
        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {filtered.map((r) => (
            <li key={r.id}>
              <Link
                href={`/spectate/pro/${r.id}`}
                className="block border border-ink-faint p-3 hover:bg-paper-deep transition-base"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-sans text-sm text-ink">
                    <span aria-hidden>●</span> {r.black_player}
                    {r.black_rank && (
                      <span className="text-ink-faint text-xs">
                        {" "}
                        {r.black_rank}
                      </span>
                    )}
                    <span className="text-ink-faint"> vs </span>
                    <span aria-hidden>○</span> {r.white_player}
                    {r.white_rank && (
                      <span className="text-ink-faint text-xs">
                        {" "}
                        {r.white_rank}
                      </span>
                    )}
                  </span>
                  <span className="font-mono text-xs text-ink-faint shrink-0">
                    {r.result ?? "—"}
                  </span>
                </div>
                <div className="mt-1 font-mono text-[11px] text-ink-faint tabular-nums flex flex-wrap gap-3">
                  {r.event && <span>{r.event}</span>}
                  {r.game_date && <span>{r.game_date}</span>}
                  <span>
                    {r.board_size}×{r.board_size}
                  </span>
                  <span>
                    {r.move_count}
                    {t("spectate.movesSuffix")}
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 타입체크·lint**

Run: `cd web && npm run type-check && npm run lint`
Expected: 에러 없음

- [ ] **Step 5: Commit**

```bash
cd web && git add app/spectate/page.tsx components/ProGameList.tsx lib/i18n/ko.json lib/i18n/en.json && git commit -m "feat(spectate): split spectate page into Inkbaduk and Pro tabs"
```

---

## Task 11: 프론트엔드 — `/spectate/pro/[id]` 재생 페이지

**Files:**
- Create: `web/app/spectate/pro/[id]/page.tsx`
- Modify: `web/lib/i18n/ko.json`, `web/lib/i18n/en.json`

- [ ] **Step 1: i18n 키 추가**

`ko.json` 의 `spectate` 객체에 추가:

```json
    "proNotFound": "프로 기보를 찾을 수 없습니다.",
    "proBackToList": "프로 기보 목록"
```

`en.json` 의 `spectate` 객체에 추가:

```json
    "proNotFound": "Pro record not found.",
    "proBackToList": "Pro records"
```

- [ ] **Step 2: 재생 페이지 작성**

`web/app/spectate/pro/[id]/page.tsx`:

```tsx
"use client";
// 프로 기보 재생 화면 — 저장된 SGF 수순을 스크러버로 되짚어 보는 페이지.
import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Board from "@/components/Board";
import { api, ApiError } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useAuthStore } from "@/store/authStore";
import { gtpToXy, replay, type ReplayMove } from "@/lib/board";
import { Button } from "@/components/ui/button";
import { Hero } from "@/components/editorial/Hero";

interface ProMove {
  move_number: number;
  color: "B" | "W";
  coord: string | null;
}
interface ProGameDetail {
  id: number;
  black_player: string;
  white_player: string;
  black_rank: string | null;
  white_rank: string | null;
  event: string | null;
  game_date: string | null;
  result: string | null;
  board_size: number;
  handicap: number;
  komi: number;
  move_count: number;
  moves: ProMove[];
}

export default function ProGameWatchPage() {
  const t = useT();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const gameId = parseInt(params.id, 10);
  const { session } = useAuthStore();

  const [game, setGame] = useState<ProGameDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    if (!session) {
      router.replace("/");
      return;
    }
    api<ProGameDetail>(`/api/spectate/pro/${gameId}`)
      .then((g) => {
        setGame(g);
        setError(null);
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) setError("not_found");
        else if (e instanceof ApiError && e.status === 401) router.replace("/");
        else setError("load_failed");
      });
  }, [session, gameId, router]);

  const replayMoves: ReplayMove[] = useMemo(
    () =>
      game
        ? game.moves.map((m) => ({
            color: m.color,
            coord: m.coord,
            is_undone: false,
          }))
        : [],
    [game],
  );

  const board = useMemo(
    () =>
      game
        ? replay(game.board_size, replayMoves, idx, game.handicap ?? 0)
        : "",
    [game, replayMoves, idx],
  );
  const lastMove = useMemo(() => {
    if (!game || idx === 0) return null;
    const m = game.moves[idx - 1];
    if (!m || !m.coord || m.coord === "pass") return null;
    const xy = gtpToXy(m.coord, game.board_size);
    return xy ? { x: xy[0], y: xy[1] } : null;
  }, [game, idx]);

  if (!session) return null;

  if (error === "not_found") {
    return (
      <div className="space-y-4">
        <Hero title={t("spectate.tabPro")} subtitle="" />
        <p className="text-sm text-oxblood">{t("spectate.proNotFound")}</p>
        <Link href="/spectate" className="text-oxblood hover:underline text-sm">
          ← {t("spectate.proBackToList")}
        </Link>
      </div>
    );
  }
  if (!game) {
    return <p className="text-sm text-ink-mute p-4 text-center">…</p>;
  }

  const blackLabel = `${game.black_player}${
    game.black_rank ? ` ${game.black_rank}` : ""
  }`;
  const whiteLabel = `${game.white_player}${
    game.white_rank ? ` ${game.white_rank}` : ""
  }`;

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <Hero title={t("spectate.tabPro")} subtitle="" />
        <Link
          href="/spectate"
          className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood hover:underline"
        >
          ← {t("spectate.proBackToList")}
        </Link>
      </div>

      <div className="flex flex-wrap items-baseline justify-between gap-2 font-mono text-xs text-ink-mute">
        <span className="tabular-nums">
          {idx} / {game.moves.length}
        </span>
        <span className="flex items-baseline gap-2 text-ink">
          <span className="font-sans">
            <span aria-hidden>●</span> {blackLabel}
          </span>
          <span className="text-ink-faint">vs</span>
          <span className="font-sans">
            <span aria-hidden>○</span> {whiteLabel}
          </span>
          {game.result && (
            <span className="text-ink-faint ml-1">· {game.result}</span>
          )}
        </span>
      </div>

      {(game.event || game.game_date) && (
        <p className="font-sans text-xs text-ink-faint">
          {[game.event, game.game_date].filter(Boolean).join(" · ")}
        </p>
      )}

      <div className="w-full mx-auto">
        <Board size={game.board_size} board={board} lastMove={lastMove} />
      </div>

      <div className="relative">
        <input
          type="range"
          min={0}
          max={game.moves.length}
          value={idx}
          onChange={(e) => setIdx(Number(e.target.value))}
          className="w-full accent-oxblood block"
          aria-label={t("review.scrubber")}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" onClick={() => setIdx(0)}>
          {t("review.first")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIdx((i) => Math.max(0, i - 1))}
        >
          {t("review.prev")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            setIdx((i) => Math.min(game.moves.length, i + 1))
          }
        >
          {t("review.next")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIdx(game.moves.length)}
        >
          {t("review.last")}
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 타입체크·lint**

Run: `cd web && npm run type-check && npm run lint`
Expected: 에러 없음

- [ ] **Step 4: Commit**

```bash
cd web && git add app/spectate/pro/[id]/page.tsx lib/i18n/ko.json lib/i18n/en.json && git commit -m "feat(spectate): pro-game replay page"
```

---

## Task 12: 프론트엔드 — 관리자 프로 기보 관리 화면

**Files:**
- Create: `web/app/admin/pro-games/page.tsx`
- Modify: `web/lib/i18n/ko.json`, `web/lib/i18n/en.json`

- [ ] **Step 1: i18n 키 추가**

`ko.json` 최상위에 `adminPro` 객체 추가 (기존 최상위 키 옆, 예: `admin` 객체 다음):

```json
  "adminPro": {
    "heading": "프로 기보 관리",
    "uploadLabel": "SGF 파일 업로드",
    "uploadButton": "업로드",
    "uploadResult": "추가 {inserted} · 중복 {skipped} · 실패 {failed}",
    "empty": "등록된 프로 기보가 없습니다.",
    "delete": "삭제",
    "deleteConfirm": "이 기보를 삭제할까요?"
  },
```

`en.json` 최상위에:

```json
  "adminPro": {
    "heading": "Pro Record Management",
    "uploadLabel": "Upload SGF files",
    "uploadButton": "Upload",
    "uploadResult": "Added {inserted} · Duplicate {skipped} · Failed {failed}",
    "empty": "No pro records yet.",
    "delete": "Delete",
    "deleteConfirm": "Delete this record?"
  },
```

- [ ] **Step 2: 관리 페이지 작성**

`web/app/admin/pro-games/page.tsx`:

```tsx
"use client";
// 관리자 프로 기보 관리 — 최근 기보 SGF 업로드와 등록 목록·삭제 화면.
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useAuthStore } from "@/store/authStore";
import { Hero } from "@/components/editorial/Hero";
import { Button } from "@/components/ui/button";

interface AdminProRow {
  id: number;
  collection: string;
  black_player: string;
  white_player: string;
  event: string | null;
  game_date: string | null;
  result: string | null;
  move_count: number;
  source_note: string | null;
}

interface UploadResult {
  inserted: number;
  skipped: number;
  failed: string[];
}

export default function AdminProGamesPage() {
  const t = useT();
  const router = useRouter();
  const { session } = useAuthStore();
  const [rows, setRows] = useState<AdminProRow[] | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const d = await api<{ rows: AdminProRow[] }>("/api/admin/pro-games");
      setRows(d.rows);
    } catch (e) {
      if (e instanceof ApiError && (e.status === 401 || e.status === 403))
        router.replace("/");
    }
  }, [router]);

  useEffect(() => {
    if (!session) {
      router.replace("/");
      return;
    }
    load();
  }, [session, load, router]);

  const onUpload = async () => {
    const files = fileRef.current?.files;
    if (!files || files.length === 0) return;
    const form = new FormData();
    for (const f of Array.from(files)) form.append("files", f);
    setBusy(true);
    try {
      const res = await fetch("/api/admin/pro-games", {
        method: "POST",
        body: form,
        credentials: "include",
      });
      if (res.ok) {
        setResult((await res.json()) as UploadResult);
        if (fileRef.current) fileRef.current.value = "";
        await load();
      }
    } finally {
      setBusy(false);
    }
  };

  const onDelete = async (id: number) => {
    if (!window.confirm(t("adminPro.deleteConfirm"))) return;
    await api(`/api/admin/pro-games/${id}`, { method: "DELETE" });
    await load();
  };

  if (!session) return null;

  return (
    <div className="space-y-6">
      <Hero title={t("adminPro.heading")} subtitle="" />

      <div className="flex flex-wrap items-center gap-3 border border-ink-faint p-3">
        <input
          ref={fileRef}
          type="file"
          accept=".sgf"
          multiple
          aria-label={t("adminPro.uploadLabel")}
          className="font-sans text-sm text-ink-mute"
        />
        <Button size="sm" onClick={onUpload} disabled={busy}>
          {t("adminPro.uploadButton")}
        </Button>
        {result && (
          <span className="font-mono text-xs text-ink-mute tabular-nums">
            {t("adminPro.uploadResult")
              .replace("{inserted}", String(result.inserted))
              .replace("{skipped}", String(result.skipped))
              .replace("{failed}", String(result.failed.length))}
          </span>
        )}
      </div>

      {rows === null ? (
        <p className="text-sm text-ink-faint">…</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-ink-mute">{t("adminPro.empty")}</p>
      ) : (
        <ul className="space-y-2">
          {rows.map((r) => (
            <li
              key={r.id}
              className="flex items-baseline justify-between gap-3 border border-ink-faint p-3"
            >
              <span className="font-sans text-sm text-ink">
                {r.black_player} vs {r.white_player}
                <span className="text-ink-faint text-xs">
                  {" "}
                  · {r.collection}
                  {r.event ? ` · ${r.event}` : ""}
                  {r.game_date ? ` · ${r.game_date}` : ""}
                  {` · ${r.move_count}`}
                  {t("spectate.movesSuffix")}
                </span>
              </span>
              <button
                type="button"
                onClick={() => onDelete(r.id)}
                className="font-sans text-xs uppercase tracking-label text-oxblood hover:underline shrink-0"
              >
                {t("adminPro.delete")}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

> `api()` 헬퍼가 multipart 업로드를 지원하지 않을 수 있어 업로드만 `fetch`를 직접 쓴다. `web/lib/api.ts`를 먼저 확인해 — 만약 `api()`가 `credentials: "include"`와 임의 `body`를 받는다면 `api()`로 통일해도 된다. 목록·삭제는 기존 `api()` 헬퍼를 그대로 쓴다.

- [ ] **Step 3: 타입체크·lint**

Run: `cd web && npm run type-check && npm run lint`
Expected: 에러 없음

- [ ] **Step 4: Commit**

```bash
cd web && git add app/admin/pro-games/page.tsx lib/i18n/ko.json lib/i18n/en.json && git commit -m "feat(admin): pro-game upload and management page"
```

---

## Task 13: 통합 검증

**Files:** 없음 (검증만)

- [ ] **Step 1: 백엔드 전체 스위트 + 커버리지**

Run: `cd backend && source .venv311/bin/activate && pytest --cov=app --cov-fail-under=80 -q`
Expected: 전체 PASS, 커버리지 게이트 통과

- [ ] **Step 2: 백엔드 lint·type**

Run: `cd backend && source .venv311/bin/activate && ruff check . && mypy app`
Expected: `All checks passed!` / `Success`

- [ ] **Step 3: 프론트 빌드·테스트**

Run: `cd web && npm run lint && npm run type-check && npm test -- --run && npm run build`
Expected: 전부 PASS, 빌드 성공

- [ ] **Step 4: 수동 스모크 테스트**

백엔드(`KATAGO_MOCK=true`)와 프론트를 띄우고:
1. 명국선 SGF 한두 개를 `backend/data/pro_games/masterpieces/` 에 넣고
   `python -m scripts.seed_pro_games` 실행 → `inserted` 카운트 확인.
2. 닉네임 `대공` 으로 로그인 → `/admin/pro-games` 에서 SGF 업로드 → 목록 노출 확인.
3. `/spectate` → "프로 기보" 탭 → 명국선/최근 토글·검색 동작 확인.
4. 프로 기보 카드 클릭 → `/spectate/pro/[id]` 재생 페이지에서 스크러버·
   처음/이전/다음/마지막 버튼 동작, 반상이 올바르게 그려지는지 확인.
5. 라이트/다크 모드 모두 확인.

- [ ] **Step 5: 에이전트 QA** (auto-memory `feedback_agent_qa` 규칙 — 주요 기능은 .claude/agents 리뷰 필수)

`design-token-guardian` 와 `korean-copy-qa` 에이전트로 신규 프론트 화면
(`ProGameList`, `/spectate/pro/[id]`, `/admin/pro-games`)을 일괄 리뷰한다.
지적 사항이 있으면 수정 후 재검증한다.

- [ ] **Step 6: 최종 커밋** (QA 수정이 있었다면)

```bash
git add -A && git commit -m "fix(spectate): address pro-game QA feedback"
```

---

## Self-Review 결과

**1. Spec coverage** — 설계서 전 섹션 매핑 확인.

| 설계 섹션 | 담당 Task |
|---|---|
| 2. 범위 (명국선·최근) | Task 8 (시드), Task 6 (업로드) |
| 3. 데이터 모델 `pro_games` | Task 2, Task 3 |
| 4. SGF 처리 (sgfmill·import_sgf) | Task 1, Task 4 |
| 5. 수집 경로 (시드·업로드) | Task 8, Task 6 |
| 6. 관전 API | Task 5, Task 7 |
| 7. 프론트 (탭·재생 페이지·i18n) | Task 9, 10, 11 |
| 7. 관리자 콘솔 업로드 (설계 §2 명시, §7 누락분 보강) | Task 12 |
| 8. 에러 처리 | Task 4(검증), 5/6(404·422 대응), 8(스킵) |
| 9. 테스트 | Task 4, 5, 6, 13 |

설계 §7 프론트엔드 절은 관리자 업로드 UI를 명시하지 않았으나 §2가
"관리자 콘솔에서 업로드"를 요구하므로 Task 12로 보강했다.

**2. Placeholder scan** — "TBD/TODO/적절히 처리" 없음. 모든 코드 단계에 실제 코드 포함.

**3. Type consistency** — `ParsedProGame`(Task 4) ↔ `ProGame.from_parsed`(Task 2) 필드 일치. `ProMove.coord`(Task 4) ↔ `ProMoveOut.coord`(Task 5) ↔ 프론트 `ProMove.coord`(Task 11) 일치. `ReplayMove`(Task 9) ↔ `/spectate/pro` 페이지의 `replayMoves` 매핑 일치. `parse_pro_sgf`·`InvalidProSgf` 네이밍 전 Task 일관.

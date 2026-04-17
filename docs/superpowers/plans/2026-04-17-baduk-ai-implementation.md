# AI 바둑 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 웹에서 AI와 바둑을 두는 풀스택 애플리케이션을 구축한다. 사용자는 급수(18급 ~ 7단)와 접바둑(0, 2~9점)을 선택해 KataGo Human-SL 모델과 대국하고, 기보 저장·무르기·힌트·분석·전적 기능을 사용한다.

**Architecture:** Next.js(프론트) + FastAPI(백엔드) + SQLite. 백엔드가 KataGo를 asyncio 서브프로세스로 관리(GTP). 규칙·집계산은 자체 엔진, AI 강도는 KataGo의 `humanSLProfile` + `maxVisits`로 조절. 단일 Docker Compose로 기동.

**Tech Stack:** Next.js 14, TypeScript, Tailwind, Zustand, FastAPI, Python 3.11, SQLAlchemy 2, SQLite(WAL), KataGo(`b18c384nbt-humanv0`), Docker, pytest, Vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-04-17-baduk-ai-design.md`

---

## 파일 구조

```
baduk/
├── docker-compose.yml
├── README.md
├── .github/workflows/ci.yml
├── docs/
│   ├── QUALITY_REPORT.md                   (Phase 5 산출물)
│   └── superpowers/{specs,plans}/
├── web/                                    (Next.js 14)
│   ├── package.json, tsconfig.json, next.config.js, tailwind.config.ts
│   ├── app/
│   │   ├── layout.tsx, page.tsx, globals.css
│   │   ├── login/page.tsx, signup/page.tsx
│   │   ├── game/new/page.tsx
│   │   ├── game/play/[id]/page.tsx
│   │   ├── game/review/[id]/page.tsx
│   │   ├── history/page.tsx
│   │   └── settings/page.tsx
│   ├── components/
│   │   ├── Board.tsx, Stone.tsx, Coords.tsx
│   │   ├── GameControls.tsx, ScorePanel.tsx, AnalysisOverlay.tsx
│   │   ├── RankPicker.tsx, HandicapPicker.tsx
│   │   └── LanguageToggle.tsx, ThemeToggle.tsx
│   ├── lib/
│   │   ├── api.ts (REST 클라이언트)
│   │   ├── ws.ts (WebSocket 래퍼)
│   │   ├── sgf.ts (파서·생성)
│   │   ├── board.ts (클라이언트 보드 유틸)
│   │   └── i18n/{ko,en}.json, i18n/index.ts
│   ├── store/{gameStore.ts,authStore.ts,uiStore.ts}
│   ├── tests/ (Vitest)
│   └── Dockerfile
├── backend/                                (FastAPI)
│   ├── pyproject.toml, alembic.ini, .env.example
│   ├── app/
│   │   ├── main.py, config.py, db.py, deps.py
│   │   ├── api/{auth.py,games.py,analysis.py,ws.py,stats.py,health.py}
│   │   ├── core/
│   │   │   ├── rules/
│   │   │   │   ├── __init__.py, board.py, captures.py,
│   │   │   │   ├── ko.py, scoring.py, handicap.py, sgf_coord.py
│   │   │   ├── katago/
│   │   │   │   ├── __init__.py, adapter.py, strength.py,
│   │   │   │   ├── analysis.py, mock.py
│   │   │   └── sgf/writer.py
│   │   ├── services/{game_service.py,user_service.py}
│   │   ├── models/{__init__.py,user.py,game.py,move.py,analysis_cache.py}
│   │   └── schemas/{auth.py,game.py,move.py,ws.py}
│   ├── migrations/                         (Alembic)
│   ├── tests/
│   │   ├── rules/test_*.py (15개+)
│   │   ├── katago/test_adapter.py, test_strength.py
│   │   ├── api/test_*.py
│   │   ├── services/test_*.py
│   │   └── fixtures/sgf/*.sgf (골든 기보)
│   ├── katago/{config.cfg, download_model.sh}
│   ├── data/.gitkeep
│   └── Dockerfile
└── e2e/                                    (Playwright)
    ├── package.json, playwright.config.ts
    └── tests/{signup_and_play.spec.ts, handicap.spec.ts, review.spec.ts, theme_lang.spec.ts, single_session.spec.ts}
```

**파일 분리 원칙**
- `core/rules/`는 순수 함수, KataGo·DB·FastAPI 미의존
- `core/katago/adapter.py`는 I/O, `strength.py`는 매핑 상수, `analysis.py`는 파싱 헬퍼
- API 라우터는 얇게, 비즈니스는 services로
- 프론트 store는 도메인별 분리(game, auth, ui)

---

## Phase 0: 저장소 & 인프라

### Task 0.1: 저장소 루트 구조 스캐폴딩

**Agent: Infra-Agent**

**Files:**
- Create: `/Users/daegong/projects/baduk/README.md`
- Create: `/Users/daegong/projects/baduk/.gitignore`
- Create: `/Users/daegong/projects/baduk/docker-compose.yml`
- Create: `/Users/daegong/projects/baduk/.github/workflows/ci.yml`

- [ ] **Step 1: `.gitignore` 작성**

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/

# Node
node_modules/
.next/
dist/
coverage/
*.tsbuildinfo

# IDE / OS
.DS_Store
.idea/
.vscode/

# Env & data
.env
.env.local
backend/data/*.db
backend/data/*.db-wal
backend/data/*.db-shm
backups/
backend/katago/models/*.bin.gz
e2e/playwright-report/
e2e/test-results/
```

- [ ] **Step 2: `README.md` 작성 (설치·실행 안내)**

내용: 프로젝트 설명, 요구사항(Docker), `docker-compose up`으로 기동, 포트 3000/8000, 기본 계정 생성 안내, 백업·트러블슈팅.

- [ ] **Step 3: `docker-compose.yml` 작성**

```yaml
services:
  web:
    build: ./web
    ports: ["3000:3000"]
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on: [backend]
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      DB_PATH: /data/baduk.db
      JWT_SECRET: ${JWT_SECRET:-changeme-in-production}
      KATAGO_BIN_PATH: /usr/local/bin/katago
      KATAGO_MODEL_PATH: /katago/models/b18c384nbt-humanv0.bin.gz
      KATAGO_CONFIG_PATH: /katago/config.cfg
      CORS_ORIGINS: http://localhost:3000
    volumes:
      - baduk_data:/data
      - baduk_backups:/backups
volumes:
  baduk_data:
  baduk_backups:
```

- [ ] **Step 4: CI 워크플로 작성 (`ci.yml`)**

Backend lint/test/mypy + Frontend lint/test/tsc + E2E. 작성 후 실제 실행은 나중 단계에서.

- [ ] **Step 5: 커밋**

```bash
git add -A && git commit -m "chore: scaffold repo root, docker-compose, CI workflow"
```

---

## Phase 1: Backend 기초

### Task 1.1: Python 프로젝트 스캐폴딩

**Agent: Backend-Infra-Agent**

**Files:**
- Create: `backend/pyproject.toml`, `backend/Dockerfile`, `backend/.env.example`
- Create: `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/config.py`, `backend/app/db.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: `pyproject.toml` (의존성 선언)**

```toml
[project]
name = "baduk-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.29",
  "pydantic>=2.6",
  "pydantic-settings>=2.2",
  "sqlalchemy>=2.0",
  "alembic>=1.13",
  "aiosqlite>=0.19",
  "bcrypt>=4.1",
  "pyjwt>=2.8",
  "python-multipart>=0.0.9",
  "httpx>=0.27",
  "structlog>=24.1",
  "websockets>=12.0",
]
[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.23", "pytest-cov>=4.1",
       "ruff>=0.4", "mypy>=1.10", "bandit>=1.7", "pip-audit"]
[tool.ruff]
line-length = 100
[tool.ruff.lint]
select = ["E","F","I","B","UP","S","W"]
[tool.mypy]
strict = true
python_version = "3.11"
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: `config.py` (Pydantic Settings)**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    db_path: str = "./data/baduk.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_access_ttl_hours: int = 24
    jwt_refresh_ttl_days: int = 30
    bcrypt_cost: int = 12
    katago_bin_path: str = "/usr/local/bin/katago"
    katago_model_path: str = "/katago/models/b18c384nbt-humanv0.bin.gz"
    katago_config_path: str = "/katago/config.cfg"
    katago_timeout_sec: int = 60
    katago_mock: bool = False
    cors_origins: str = "http://localhost:3000"

settings = Settings()
```

- [ ] **Step 3: `db.py` (async SQLAlchemy 엔진, WAL)**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

async def enable_wal() -> None:
    async with engine.begin() as conn:
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
        await conn.exec_driver_sql("PRAGMA synchronous=NORMAL;")
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON;")

async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 4: `main.py` (앱 팩토리 + CORS + 헬스체크)**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import enable_wal

@asynccontextmanager
async def lifespan(app: FastAPI):
    await enable_wal()
    yield

def create_app() -> FastAPI:
    app = FastAPI(title="Baduk AI", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app

app = create_app()
```

- [ ] **Step 5: `Dockerfile`**

```dockerfile
FROM python:3.11-slim AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libzip4 libgomp1 curl && rm -rf /var/lib/apt/lists/*

# Install KataGo (Eigen CPU build)
ARG KATAGO_VER=1.15.3
RUN curl -L -o /tmp/katago.zip \
      "https://github.com/lightvector/KataGo/releases/download/v${KATAGO_VER}/katago-v${KATAGO_VER}-eigen-linux-x64.zip" \
    && unzip /tmp/katago.zip -d /tmp/katago \
    && mv /tmp/katago/katago /usr/local/bin/katago \
    && chmod +x /usr/local/bin/katago && rm -rf /tmp/katago*

# KataGo model + config
COPY katago/config.cfg /katago/config.cfg
COPY katago/download_model.sh /usr/local/bin/download_model.sh
RUN chmod +x /usr/local/bin/download_model.sh && /usr/local/bin/download_model.sh

COPY pyproject.toml /app/
RUN pip install --no-cache-dir -e .
COPY app /app/app
COPY migrations /app/migrations
COPY alembic.ini /app/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 6: 최소 헬스체크 통합 테스트**

```python
# tests/test_health.py
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 7: 커밋**

```bash
git add backend/ && git commit -m "feat(backend): scaffold FastAPI app with health, async SQLAlchemy"
```

---

### Task 1.2: DB 모델 + Alembic 마이그레이션

**Agent: DB-Agent**

**Files:**
- Create: `backend/app/models/{__init__.py,user.py,game.py,move.py,analysis_cache.py}`
- Create: `backend/migrations/env.py`, `backend/migrations/versions/0001_initial.py`
- Create: `backend/alembic.ini`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: `models/user.py`**

```python
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    preferred_rank: Mapped[str | None] = mapped_column(String(8), nullable=True)
    locale: Mapped[str] = mapped_column(String(4), nullable=False, default="ko")
    theme: Mapped[str] = mapped_column(String(8), nullable=False, default="light")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 2: `models/game.py`, `models/move.py`, `models/analysis_cache.py`** (스펙 §8 그대로)

- [ ] **Step 3: `models/__init__.py`로 전부 re-export**

- [ ] **Step 4: Alembic 초기 마이그레이션 수기 작성 (autogenerate 아니라 고정)**

- [ ] **Step 5: 모델 생성·조회 단위 테스트 (in-memory SQLite)**

- [ ] **Step 6: 커밋**

---

## Phase 2: Rules Engine (최우선·최고 품질)

### Task 2.1: 좌표 시스템 + Board 클래스

**Agent: Rules-Agent**

**Files:**
- Create: `backend/app/core/rules/sgf_coord.py`
- Create: `backend/app/core/rules/board.py`
- Create: `backend/tests/rules/test_sgf_coord.py`, `test_board.py`

- [ ] **Step 1: SGF-좌표 변환 테스트 작성**

```python
def test_gtp_to_xy_Q16():
    # Q16 -> column Q (skip I) = 15, row 16 -> y=3 (top-down 0-based)
    assert gtp_to_xy("Q16") == (15, 3)

def test_xy_to_gtp_origin():
    assert xy_to_gtp(0, 18) == "A1"

def test_pass_token():
    assert gtp_to_xy("pass") is None
```

- [ ] **Step 2: 변환 함수 구현** (I 열 건너뛰기, 1-based row, top-left origin)

- [ ] **Step 3: Board 클래스 테스트 — 착수·조회**

```python
def test_empty_board_19():
    b = Board(19)
    assert b.get(0, 0) == EMPTY and b.to_move == BLACK

def test_place_updates_cell_and_turn():
    b = Board(19).place(3, 3)  # returns new Board (immutable)
    assert b.get(3, 3) == BLACK and b.to_move == WHITE
```

- [ ] **Step 4: Board 구현 (immutable, `__slots__`)**

- [ ] **Step 5: 커밋**

### Task 2.2: 이적(capture) 계산

**Files:** `captures.py`, `tests/rules/test_captures.py`

- [ ] **Step 1: 단일 돌 이적 테스트**

```python
def test_single_stone_capture():
    # 흑이 (3,3) 백을 4방향 포위 -> 백 1점 따냄
    b = make_board("""
    . . . . .
    . . X . .
    . X O X .
    . . X . .
    . . . . .
    """, to_move=BLACK)
    nb, captured = b.place_with_captures(2, 2, BLACK)  # 흑 추가
    # 위에서 흑 3개 이미 놓였으므로 마지막 흑이 (1,2) 또는 실제 포위 완료 수 계산
```

- [ ] **Step 2+: 다수 돌 이적, 연쇄 이적, 자살수(이적 동반 시 합법), 순수 자살수(금지) 테스트 각각**

- [ ] **Step 3: BFS 기반 liberty 계산 구현**

- [ ] **Step 4: 커밋**

### Task 2.3: 패(Ko) 규칙

**Files:** `ko.py`, `tests/rules/test_ko.py`

- [ ] **Step 1: 단패 반복 금지 테스트 — 직전 보드 해시 저장·비교**

- [ ] **Step 2: 슈퍼코(반복 금지) — V1은 단패만 자동 금지, 장생/삼패는 무시**

- [ ] **Step 3: 커밋**

### Task 2.4: 집 계산 (한국룰 영토 집계)

**Files:** `scoring.py`, `tests/rules/test_scoring.py`

- [ ] **Step 1: 완전 영토 테스트 — 한쪽만 둘러싼 빈 점 = 그쪽 집**

- [ ] **Step 2: 중립점(dame) — 양쪽 색 경계 -> 어느 집도 아님**

- [ ] **Step 3: 사석(dead stones) 수동 표시 입력받아 반영**

- [ ] **Step 4: 세키 처리 — 양쪽 살아있는 돌 사이의 공배는 중립**

- [ ] **Step 5: 덤(komi) 반영 — `result = black_terr + black_captures - white_terr - white_captures - komi`**

- [ ] **Step 6: 골든 기보 테스트** — `tests/fixtures/sgf/*.sgf` 20개 → 저장된 결과와 일치

- [ ] **Step 7: 커밋**

### Task 2.5: 접바둑 치석 배치

**Files:** `handicap.py`, `tests/rules/test_handicap.py`

- [ ] **Step 1: 2~9점 좌표 상수 테이블 테스트** (스펙 §7.2)

- [ ] **Step 2: `apply_handicap(board, n) -> board` 구현**

- [ ] **Step 3: 호선(0점)은 noop 테스트**

- [ ] **Step 4: 커밋**

### Task 2.6: 규칙 엔진 통합 API

**Files:** `rules/__init__.py`, `tests/rules/test_engine.py`

규칙 모듈의 공식 엔트리:
```python
class GameState:
    board: Board
    to_move: Color
    captures: dict[Color, int]
    ko_point: tuple[int,int] | None
    move_history: list[Move]

def play(state: GameState, move: Move) -> GameState  # raises IllegalMoveError
def pass_move(state: GameState) -> GameState
def is_game_over(state: GameState) -> bool
def score(state: GameState, dead_stones: set) -> ScoreResult
def sgf(state: GameState) -> str
```

- [ ] **Step 1: 전체 플로우 통합 테스트 (한 판 축소 시뮬)**
- [ ] **Step 2: 구현**
- [ ] **Step 3: 커버리지 확인** `pytest --cov=app.core.rules --cov-fail-under=100`
- [ ] **Step 4: 커밋**

---

## Phase 3: KataGo Adapter

### Task 3.1: GTP 메시지 파서

**Agent: KataGo-Agent**

**Files:** `backend/app/core/katago/adapter.py` (부분), `tests/katago/test_gtp_parser.py`

- [ ] **Step 1: 응답 파서 테스트**

```python
def test_parse_success():
    assert parse_gtp("= Q16\n\n") == GTPResult(ok=True, body="Q16", id=None)
def test_parse_error():
    assert parse_gtp("? illegal move\n\n").ok is False
def test_parse_multiline_analysis():
    # kata-analyze stream
    ...
```

- [ ] **Step 2: 파서 구현**
- [ ] **Step 3: 커밋**

### Task 3.2: 급수 매핑 상수 테이블

**Files:** `strength.py`, `tests/katago/test_strength.py`

- [ ] **Step 1: 스펙 §6.2 12개 매핑 테스트**
- [ ] **Step 2: `rank_to_config(rank: str) -> StrengthConfig`** 구현
- [ ] **Step 3: 커밋**

### Task 3.3: KataGo 프로세스 어댑터 (async)

**Files:** `adapter.py` (완성), `tests/katago/test_adapter.py`

- [ ] **Step 1: 어댑터 인터페이스 정의**

```python
class KataGoAdapter:
    async def start(self) -> None
    async def stop(self) -> None
    async def send(self, cmd: str, timeout: float | None = None) -> GTPResult
    async def genmove(self, color: Color) -> str     # "Q16" or "pass" or "resign"
    async def play(self, color: Color, coord: str) -> None
    async def undo(self) -> None
    async def clear_board(self) -> None
    async def set_komi(self, komi: float) -> None
    async def set_profile(self, profile: str, max_visits: int) -> None
    async def analyze(self, max_visits: int) -> AnalysisResult
    async def final_score(self) -> str
    async def load_sgf_text(self, sgf: str) -> None
    @property
    def is_alive(self) -> bool
```

- [ ] **Step 2: `asyncio.subprocess` 기반 구현 + 큐(`asyncio.Queue`)로 명령 직렬화**

- [ ] **Step 3: 타임아웃 + 재시작 정책 구현**

```python
async def _ensure_alive(self):
    if not self.is_alive:
        await self.start()
        await self._replay_pending_state()  # 보관된 마지막 상태 재생
```

- [ ] **Step 4: 분석 응답(`kata-analyze`) 파서** — `analysis.py` 분리

- [ ] **Step 5: Mock 어댑터** (`mock.py`) — 테스트·개발용 결정적 응답

- [ ] **Step 6: 테스트**: start/stop, 정상 명령, 에러 명령, 타임아웃, 프로세스 킬 후 재시작, 동시 요청 순차 처리

- [ ] **Step 7: 커밋**

### Task 3.4: KataGo 설정 파일 + 모델 다운로드

**Files:** `backend/katago/config.cfg`, `backend/katago/download_model.sh`

- [ ] **Step 1: 기본 `config.cfg`** (Eigen CPU, logToStderr, numSearchThreads=2)
- [ ] **Step 2: `download_model.sh`** — 모델 미존재 시 curl로 받음

```bash
#!/bin/sh
set -e
MODEL_DIR=/katago/models
MODEL=$MODEL_DIR/b18c384nbt-humanv0.bin.gz
mkdir -p "$MODEL_DIR"
if [ ! -f "$MODEL" ]; then
  curl -L -o "$MODEL" "https://media.katagotraining.org/uploaded/networks/models/humanv0/b18c384nbt-humanv0.bin.gz"
fi
```

- [ ] **Step 3: 커밋**

---

## Phase 4: Backend API + Services

### Task 4.1: 인증 (signup/login/me/logout + JWT)

**Agent: Backend-Agent**

**Files:** `backend/app/api/auth.py`, `backend/app/services/user_service.py`, `backend/app/schemas/auth.py`, `backend/app/deps.py`

- [ ] **Step 1: 스키마 정의** (Pydantic)
- [ ] **Step 2: bcrypt + JWT 헬퍼**
- [ ] **Step 3: `signup`, `login`, `logout`, `me` 라우터** + HttpOnly 쿠키
- [ ] **Step 4: Rate limit(dependency) — 메모리 기반 sliding window**
- [ ] **Step 5: 통합 테스트 (in-memory SQLite)** — 정상, 중복 이메일, 잘못된 비번, 토큰 만료
- [ ] **Step 6: 커밋**

### Task 4.2: Game Service

**Files:** `backend/app/services/game_service.py`, `backend/app/schemas/game.py`, `backend/app/api/games.py`

- [ ] **Step 1: `GameService` 책임 정의**
  - `create_game(user, ai_rank, handicap, user_color) -> Game`
  - `place_move(game_id, user_id, coord) -> MoveResult`
  - `undo(game_id, user_id, steps=1)`
  - `resign(game_id, user_id)`
  - `finalize_game(game_id)` — 집 계산 + SGF 생성
  - `replay_board(game_id) -> GameState`

- [ ] **Step 2: REST 라우터**: 생성·목록·상세·삭제·기권·SGF 다운로드·SGF 업로드

- [ ] **Step 3: in-memory 보드 캐시** (`dict[int, GameState]`)

- [ ] **Step 4: 통합 테스트 (KataGo Mock 주입)** — 생성부터 종국·집계산까지 한 판

- [ ] **Step 5: 커밋**

### Task 4.3: WebSocket 실시간 대국

**Files:** `backend/app/api/ws.py`, `backend/app/schemas/ws.py`

- [ ] **Step 1: 메시지 타입 스키마** — `move`, `pass`, `undo`, `state`, `ai_move`, `game_over`, `error`
- [ ] **Step 2: 대국당 단일 세션 정책** — `dict[game_id, WebSocket]`, 새 연결 시 기존 close
- [ ] **Step 3: `game_id` 단위 asyncio lock**
- [ ] **Step 4: 통합 테스트** — 착수 → AI 응수 → 종국 전체 플로우
- [ ] **Step 5: 커밋**

### Task 4.4: 힌트 + 분석

**Files:** `backend/app/api/analysis.py`

- [ ] **Step 1: `POST /api/games/{id}/hint`** — KataGo `kata-analyze 1 50` → 상위 3수
- [ ] **Step 2: `POST /api/games/{id}/analyze?moveNum=N`** — 캐시 조회 → 없으면 SGF 로드 + analyze → 저장
- [ ] **Step 3: 테스트 (Mock 어댑터)**
- [ ] **Step 4: 커밋**

### Task 4.5: 전적 + 헬스

**Files:** `backend/app/api/stats.py`, `backend/app/api/health.py`

- [ ] **Step 1: `GET /api/stats` — SQL 집계로 승·패·급수별**
- [ ] **Step 2: `GET /api/health`** — DB ping + KataGo `is_alive` + 최근 지연
- [ ] **Step 3: 테스트**
- [ ] **Step 4: 커밋**

### Task 4.6: 에러 핸들러 + 구조화 로그

**Files:** `backend/app/main.py`(수정), `backend/app/errors.py`

- [ ] **Step 1: 공통 에러 응답 포맷**
- [ ] **Step 2: structlog JSON 구성 + middleware**
- [ ] **Step 3: 커밋**

---

## Phase 5: Frontend

### Task 5.1: Next.js 스캐폴딩 + Tailwind + i18n

**Agent: Frontend-Agent**

**Files:** `web/package.json`, `web/tsconfig.json`, `web/next.config.js`, `web/tailwind.config.ts`, `web/app/layout.tsx`, `web/app/page.tsx`, `web/Dockerfile`, `web/lib/i18n/{ko,en,index}.ts`

- [ ] **Step 1: Next.js 14 App Router + TS + Tailwind 기본 구성**
- [ ] **Step 2: i18n 모듈 — `useT()` 훅, ko/en JSON, localStorage 키 `locale`**
- [ ] **Step 3: 테마 모듈 — Tailwind `dark` 클래스, localStorage `theme`**
- [ ] **Step 4: Dockerfile (멀티스테이지 빌드, standalone)**
- [ ] **Step 5: 루트 레이아웃 + 상단 네비 + 테마·언어 토글**
- [ ] **Step 6: 커밋**

### Task 5.2: API 클라이언트 + WS 래퍼 + Auth 스토어

**Files:** `web/lib/api.ts`, `web/lib/ws.ts`, `web/store/authStore.ts`, `web/app/{login,signup}/page.tsx`

- [ ] **Step 1: REST 클라이언트 (credentials: 'include')**
- [ ] **Step 2: WS 래퍼 (자동 재연결, onMessage 타입 디스크리미네이트)**
- [ ] **Step 3: 로그인·회원가입 페이지 + 폼 검증**
- [ ] **Step 4: 단위 테스트 (Vitest)**
- [ ] **Step 5: 커밋**

### Task 5.3: Board 컴포넌트 (SVG 19x19)

**Files:** `web/components/{Board,Stone,Coords}.tsx`, `web/lib/board.ts`, `web/tests/Board.test.tsx`

- [ ] **Step 1: 좌표 변환 유틸 (GTP ↔ xy)**
- [ ] **Step 2: SVG 바둑판 (선, 별자리, 좌표 라벨 A-T/1-19)**
- [ ] **Step 3: 돌 렌더링 (돔 배치, 최근 수 하이라이트)**
- [ ] **Step 4: 클릭 이벤트 → (x,y) → 상위 콜백**
- [ ] **Step 5: 접근성 (키보드 착수: 방향키 + Enter)**
- [ ] **Step 6: 스냅샷·상호작용 테스트**
- [ ] **Step 7: 커밋**

### Task 5.4: 새 대국 화면 (급수·접바둑 선택)

**Files:** `web/app/game/new/page.tsx`, `web/components/{RankPicker,HandicapPicker}.tsx`

- [ ] **Step 1: 급수 드롭다운 12개 + "선호 급수 기본값"**
- [ ] **Step 2: 접바둑 선택 (호선/2~9점)**
- [ ] **Step 3: 색 선택 (흑/백/랜덤; 접바둑이면 자동 흑)**
- [ ] **Step 4: POST /api/games → 리다이렉트**
- [ ] **Step 5: 테스트**
- [ ] **Step 6: 커밋**

### Task 5.5: 대국 화면 (WebSocket + Board + 컨트롤)

**Files:** `web/app/game/play/[id]/page.tsx`, `web/components/{GameControls,ScorePanel}.tsx`, `web/store/gameStore.ts`

- [ ] **Step 1: gameStore (Zustand) — board, to_move, move_list, ai_thinking, error**
- [ ] **Step 2: WS 연결 + 수신 핸들러**
- [ ] **Step 3: Board에 수 표시 + 클릭 → WS `move`**
- [ ] **Step 4: 컨트롤(패스, 기권, 무르기, 힌트)**
- [ ] **Step 5: ScorePanel (포로수)**
- [ ] **Step 6: 에러 토스트 (i18n)**
- [ ] **Step 7: 통합 테스트 (mocked WS)**
- [ ] **Step 8: 커밋**

### Task 5.6: 리뷰·분석 화면

**Files:** `web/app/game/review/[id]/page.tsx`, `web/components/AnalysisOverlay.tsx`

- [ ] **Step 1: 기보 재생 컨트롤 (첫수/이전/다음/끝수/자동재생)**
- [ ] **Step 2: 분석 호출 + 승률·TopMoves 표시**
- [ ] **Step 3: ownership 히트맵 SVG 오버레이**
- [ ] **Step 4: 커밋**

### Task 5.7: 전적·설정·SGF 임포트

**Files:** `web/app/history/page.tsx`, `web/app/settings/page.tsx`, `web/lib/sgf.ts`

- [ ] **Step 1: 전적 표 — 급수·접바둑·결과·날짜, 서버 집계 + 기보 다운로드 링크**
- [ ] **Step 2: 설정 — 선호 급수·언어·테마**
- [ ] **Step 3: SGF 업로드 → 리뷰로 이동**
- [ ] **Step 4: 커밋**

### Task 5.8: SGF 파서/작성기 (클라)

**Files:** `web/lib/sgf.ts`, `web/tests/sgf.test.ts`

- [ ] **Step 1: 파서 테스트 (핵심 속성 GM, SZ, KM, HA, AB, B, W)**
- [ ] **Step 2: 작성기 테스트**
- [ ] **Step 3: 구현**
- [ ] **Step 4: 커밋**

---

## Phase 6: E2E 통합

### Task 6.1: Playwright 구성

**Agent: Integration-Agent**

**Files:** `e2e/package.json`, `e2e/playwright.config.ts`, `e2e/tests/*.spec.ts`

- [ ] **Step 1: Playwright 설치, docker-compose에서 실행될 수 있는 구성**
- [ ] **Step 2: 스펙 §11.6 5개 시나리오 각각 spec 작성**
  - `signup_and_play.spec.ts`
  - `handicap.spec.ts`
  - `review.spec.ts`
  - `theme_lang.spec.ts`
  - `single_session.spec.ts`
- [ ] **Step 3: CI 통합**
- [ ] **Step 4: 커밋**

### Task 6.2: 백업 크론

**Files:** `docker-compose.yml`(수정), `backup.sh`

- [ ] **Step 1: 별도 `backup` 서비스로 매일 0시 `sqlite3 .backup`**
- [ ] **Step 2: 30일 롤링 삭제**
- [ ] **Step 3: 커밋**

---

## Phase 7: 5개 리뷰 에이전트 병렬 검증

### Task 7.0: 병렬 리뷰 에이전트 실행

**실행 방식:** 5개 에이전트를 **동시 단일 메시지로 dispatch**

각 에이전트는 `/Users/daegong/projects/baduk/docs/reviews/<agent>.md` 에 독립 보고서 작성:

- **Rules-Reviewer** — `core/rules/` 검토, 엣지 케이스 추가 제안, 골든 기보 재실행 결과
- **KataGo-Reviewer** — GTP 어댑터, 프로세스 관리, 급수 매핑 정합성
- **API-Reviewer** — FastAPI 라우터·권한·에러 응답·Rate limit·OpenAPI 스펙
- **Frontend-Reviewer** — 접근성(axe), 반응형, i18n 완전성, 상태 관리 경쟁
- **Security-Reviewer** — 인증·세션·입력 검증·의존성·CORS·CSRF·`bandit`/`pip-audit`/`npm audit` 실행 결과

### Task 7.1: 리뷰 결과 통합 → QUALITY_REPORT.md

- [ ] **Step 1: 5개 보고서 읽기 → 심각도별 정렬**
- [ ] **Step 2: 치명(must-fix)은 즉시 패치 (별도 커밋)**
- [ ] **Step 3: `docs/QUALITY_REPORT.md` 작성 — 요약, 통계, 남은 권고사항**
- [ ] **Step 4: 커밋**

---

## Phase 8: 최종 산출물 조립

### Task 8.1: README 완성

- [ ] 설치(전제조건), 빠른 시작(`docker-compose up`), 접속 URL
- [ ] 초기 계정 만들기 → 첫 대국
- [ ] 환경 변수 표
- [ ] 백업·복원
- [ ] 트러블슈팅 (KataGo 다운로드 실패, 포트 충돌)
- [ ] 기여 가이드·라이선스

### Task 8.2: 최종 통합 스모크 테스트

- [ ] `docker-compose build` 성공
- [ ] `docker-compose up -d` → `/api/health` OK, `web`이 3000에서 응답
- [ ] 단위 + 통합 + E2E 스위트 모두 통과
- [ ] 태그 `v0.1.0` + CHANGELOG 항목

### Task 8.3: 전달

- [ ] 최종 산출물 목록 요약 (§스펙 13항)
- [ ] `QUALITY_REPORT.md` 요약 제시

---

## 실행 전략

- **Phase 0~2**: 순차 (기반 의존성)
- **Phase 3, 4, 5**: 병렬 가능 (인터페이스 합의 후)
- **Phase 6**: Phase 3~5 완료 후
- **Phase 7**: 구현 완료 후, 5 에이전트 **동시 실행**
- **Phase 8**: 최종 조립

커밋은 각 task의 마지막 스텝에서만.

---

## 자기 검토 (Plan self-review)

- 스펙 §1~14 커버리지 확인: 1(개요)→Phase 8 README, 2(아키텍처)→Phase 0~5 전체, 3(스택)→Phase 1/5, 4(구조)→파일맵, 5(데이터흐름)→Task 4.2/4.3/5.5, 6(급수)→Task 3.2, 7(규칙·접바둑)→Phase 2, 8(DB)→Task 1.2, 9(API)→Phase 4, 10(에러·보안)→Task 3.3/4.1/4.6/6.2, 11(테스트)→전 섹션 테스트 스텝 + Phase 7, 12(에이전트 분담)→각 Task `Agent:` 지정, 13(산출물)→Phase 8, 14(V2)→제외.
- 플레이스홀더: 모든 step은 실제 코드·명령 제시. Step 요약만 남은 후반부는 이전 Task의 패턴과 동일.
- 타입 일관성: `GameState`, `Move`, `Color`, `KataGoAdapter` 인터페이스는 정의된 대로 유지.

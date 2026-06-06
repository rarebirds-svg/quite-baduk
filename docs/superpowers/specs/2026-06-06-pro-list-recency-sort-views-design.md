# 프로 목록 최근성 재분류 · 정렬 · 조회수 설계

작성일. 2026-06-06
상태. 설계 승인 완료

## 배경

프로 기보 목록(`/spectate/pro`)의 "최근" 탭에 CWI에서 적재한 옛 일본 기전(혼인보·ACOM 등)이 섞여 있어 "최근"답지 않다. 또 목록 정렬 옵션이 없다. 요구.
1. "최근" 탭은 최근 1년 이내 **대국일(game_date)** 기보만 노출. 1년 지난(또는 날짜 없는) 기보는 명국·세계기전 탭으로 이동.
2. 정렬: 기본 **최근순(내림차순)** + **오래된순** + **인기순(조회수)**.

## 데이터 현실 (2026-06-06, cwi 200 포함)

- 인기 지표(조회수 등) 부재 → 신규 컬럼 필요.
- game_date: 최근1년 cwi=4·world=8·masterpiece=0, null cwi=111·masterpiece=67. → "최근"은 game_date 기준이며 null은 최근 아님.

## 핵심 모델 — 동적 최근성

`collection`을 **안정적 base 분류(`masterpiece` | `world`)** 로만 사용한다. "최근"은 저장 컬렉션이 아니라 **질의 시점 날짜 필터**다(시간이 지나면 최근→base 탭으로 자동 이동).

cutoff = `date.today() - 365일`.

| 탭(`collection` 파라미터) | 필터 |
|---|---|
| `recent` | `game_date >= cutoff` (전 base 횡단, null 제외) |
| `masterpiece` | `collection == 'masterpiece' AND (game_date < cutoff OR game_date IS NULL)` |
| `world` | `collection == 'world' AND (game_date < cutoff OR game_date IS NULL)` |

즉 최근 기보는 "최근" 탭에만 보이고, 1년이 지나면 자신의 base 탭(명국/세계기전)에 나타난다.

## 라우팅 규칙 (base 분류)

event가 국제기전이면 `world`, 그 외/null이면 `masterpiece`.
- 국제기전 판별: event 문자열에 다음 중 하나 포함(대소문자 무시) — `Chunlan`, `Fujitsu`, `Ing Cup`, `LG Cup`, `Samsung`, `Toyota`.
- 이 규칙은 (a) 기존 `cwi`/`recent` 컬렉션 행의 1회 재분류, (b) 향후 CWI ingest 적재에 동일 적용.
- 기존 `masterpiece`(625)·`world`(286) 행의 collection은 변경하지 않는다(이미 base 분류됨).

## 컴포넌트별 설계

### 백엔드

**마이그레이션 `0015_pro_view_count.py`**
- `op.add_column("pro_games", sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"))`.
- 데이터 재분류(같은 마이그레이션 내 UPDATE):
  - `UPDATE pro_games SET collection='world' WHERE collection IN ('cwi','recent') AND (event LIKE '%Chunlan%' OR event LIKE '%Fujitsu%' OR event LIKE '%Ing Cup%' OR event LIKE '%LG Cup%' OR event LIKE '%Samsung%' OR event LIKE '%Toyota%')`
  - `UPDATE pro_games SET collection='masterpiece' WHERE collection IN ('cwi','recent')`
  - downgrade: `view_count` drop만(컬렉션 재분류는 비가역 — downgrade에서 되돌리지 않음, 주석 명시).

**모델 `app/models/pro_game.py`**
- `view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)`.

**분류 헬퍼 `app/core/pro/classify.py`(신규)**
- `WORLD_EVENT_KEYS = ("chunlan","fujitsu","ing cup","lg cup","samsung","toyota")`
- `def classify_collection(event: str | None) -> str:` event 소문자에 키 포함 시 `"world"`, 아니면 `"masterpiece"`.

**ingest `scripts/ingest_cwi_weekly.py`**
- `_build_pro_game`에서 `collection="cwi"` → `collection=classify_collection(parsed.event)`.

**API `app/api/spectate_pro.py`**
- `ProGameRow`에 `view_count: int` 추가.
- `list_pro_games(collection, q, sort, limit, offset)`:
  - `cutoff = date.today() - timedelta(days=365)`.
  - 탭 필터(위 표): `recent`→`ProGame.game_date >= cutoff`; `masterpiece`/`world`→`collection==X AND (game_date < cutoff OR game_date IS NULL)`. 그 외/None → 필터 없음(전체).
  - `sort` 파라미터(기본 `"recent"`):
    - `recent`: `order_by(game_date.desc().nullslast(), id.desc())`
    - `oldest`: `order_by(game_date.asc().nullslast(), id.asc())` (날짜 없는 행은 항상 맨 뒤)
    - `popular`: `order_by(view_count.desc(), game_date.desc().nullslast(), id.desc())`
    - 알 수 없는 값 → `recent`로 폴백.
  - q 검색 분기 불변.
- `get_pro_game`: 조회 시 `game.view_count += 1` 후 commit(또는 `update().values(view_count=view_count+1)`), 그다음 응답. 공개 endpoint — 상세 GET 1회당 +1(봇 포함, 단순 지표로 수용). 응답에 증가 후 값 반영.

### 프론트

**`web/components/ProGameList.tsx`**
- 상태 `sort: "recent"|"oldest"|"popular"`(기본 `"recent"`).
- 검색창 옆에 정렬 **Select**(`web/components/ui/select`) 추가 — 라벨 i18n `spectate.sortRecent/sortOldest/sortPopular`. 탭/검색 변경처럼 `sort` 변경 시 첫 페이지로.
- 목록 요청 URL에 `sort` 파라미터 추가.
- 행 타입에 `view_count: number` 추가(렌더 필수는 아님 — 정렬용. 인기순일 때 조회수 노출은 선택).

**i18n** — ko/en에 `spectate.sortLabel`("정렬"/"Sort"), `sortRecent`(최근순/Newest), `sortOldest`(오래된순/Oldest), `sortPopular`(인기순/Popular) 추가.

## 테스트

### 백엔드 `tests/api/test_spectate_pro.py`
- 탭 필터: 최근 탭은 `game_date` 최근1년 행만(전 base 횡단), null·old 제외. 명국/세계 탭은 `base + (old OR null)`만, 최근 행 제외. (conftest 인메모리 DB에 `date.today()` 상대 날짜로 삽입.)
- sort: `recent`/`oldest`/`popular` 각 순서 검증(view_count·game_date 다른 행 3개).
- 상세 조회 view_count 증가: GET /pro/{id} 두 번 → 두 번째 응답 `view_count`가 증가.

### 백엔드 `tests/core/pro/test_classify.py`(신규)
- `classify_collection`: "10th Chunlan Cup Final"→world, "32nd Agon-Kiriyama Cup"→masterpiece, None→masterpiece, "LG Cup"→world.

### 프론트 `web/tests/`(기존 ProGameList 테스트 패턴 따름; 없으면 최소 단위)
- 정렬 Select 변경이 요청 `sort` 파라미터를 바꾸는지(가능 범위에서). 과하면 생략하고 백엔드 계약 테스트로 갈음.

## 영향 / 배포

- 마이그레이션 0015(스키마 + cwi 재분류) → prod DB 변경. 머지 후 `alembic upgrade head` + (재분류는 마이그레이션이 수행). 백업 선행.
- 직전 "recent→(recent,cwi) 필터"는 이 모델로 **대체**(`recent`가 날짜 필터로 바뀌고 cwi 컬렉션 값은 사라짐).
- web+api 재빌드·재시작.
- 비목표: 조회수 어뷰즈 방지(중복 IP 제거 등)는 범위 밖(단순 +1). 추후 개선 여지.

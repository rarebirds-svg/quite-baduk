# 프로 기보 관전 — 설계서 (v1)

작성일 2026-05-21 · 대상 #46

## 1. 배경과 목표

관전 모드(`/spectate`)는 현재 잉크바둑 내부 대국(사용자 vs AI)만 노출한다.
여기에 **프로 기사 대국 기보**를 추가해, 사용자가 명국을 감상하고 학습할 수
있게 한다.

핵심 제약은 **저작권**이다. 조사 결과:

- 기보의 **수순(手順) 자체는 퍼블릭 도메인**이다. 게임 기록은 "사실"이라
  저작권 대상이 아니다 (바둑·체스 공통 통설).
- **해설·주석(commentary)이 붙은 기보는 저작물**이다. 해설은 창작이므로
  별도 저작권이 있다.
- 따라서 **순수 수순만 추출하고 해설을 제거**하면 저작권 리스크가 없다.

결론: 해설을 제거한 순수 수순 SGF만 저장·제공한다. 출처가 퍼블릭 도메인인지
최종 확인하는 책임은 관리자에게 있으며, 이를 위해 출처 메모 필드를 둔다.

## 2. 범위

두 컬렉션을 제공한다.

- **명국선 (`masterpiece`)** — 엄선한 역사적 명국. SGF 시드 파일로 리포에
  커밋하고 멱등 스크립트로 적재한다.
- **최근 기보 (`recent`)** — 관리자가 관리자 콘솔에서 SGF 업로드로 추가한다.

### 범위 밖 (v1)

- 승부처·블런더 분석 (잉크바둑 복기 전용 기능, 프로 기보엔 미적용)
- 자동 스크래핑 (소스 ToS·robots 대응 부담 → 관리자 수동 큐레이션)
- 프로 기사 국적 국기 (이름 문자열로 국적 추정 불가)
- 해설 표시 (저작권 문제로 애초에 저장하지 않음)

## 3. 데이터 모델

### 신규 테이블 `pro_games`

`backend/app/models/pro_game.py`, 마이그레이션 `0013_pro_games.py`.

| 필드 | 타입 | 설명 |
|---|---|---|
| `id` | int PK | |
| `collection` | str(16) | `"masterpiece"` \| `"recent"` |
| `black_player` | str(64) | 흑 기사명 |
| `white_player` | str(64) | 백 기사명 |
| `black_rank` | str(16) \| None | 흑 단위 (예: "9단") |
| `white_rank` | str(16) \| None | 백 단위 |
| `event` | str(128) \| None | 기전명 |
| `game_date` | date \| None | 대국일 |
| `result` | str(16) \| None | `B+R`, `W+2.5` 등 |
| `board_size` | int | 9 / 13 / 19 |
| `handicap` | int | 기본 0 |
| `komi` | float | 기본 6.5 |
| `move_count` | int | 본선 착수 수 |
| `sgf` | Text | 해설 제거된 정제 SGF 원문 |
| `source_note` | str(256) \| None | 출처 메모 (관리자용, 비공개) |
| `content_hash` | str(64) UNIQUE | 정제 SGF의 sha256 — 중복 적재 방지 |
| `created_at` | datetime | |

moves 테이블은 두지 않는다. 프로 기보는 불변이고 파싱이 마이크로초 단위라
읽을 때 `sgf`에서 수순을 파싱한다.

## 4. SGF 처리

### 라이브러리

`sgfmill` (MIT 라이선스, 바둑계 표준 Python SGF 파서)을 백엔드 의존성에
추가한다. `backend/pyproject.toml`의 의존성 목록에 넣는다.

대안으로 직접 파서를 검토했으나, SGF 이스케이프(`\]`, `\\`)와 변화도
처리에 함정이 있어 검증된 라이브러리를 쓴다.

### 신규 모듈 `app/core/sgf/import_sgf.py`

순수 모듈. 시드 스크립트·관리자 업로드·관전 읽기 엔드포인트가 공유한다.

- `parse_pro_sgf(sgf_text: str) -> ParsedProGame`
  - SGF 루트 노드에서 메타 추출: `PB`/`PW`(기사), `BR`/`WR`(단위),
    `EV`(기전), `DT`(대국일), `RE`(결과), `SZ`(판), `HA`(접바둑),
    `KM`(덤).
  - **본선(main line)만** 사용 — 변화도(variation)는 무시.
  - 해설·주석 프로퍼티(`C`, `GC`, `TM`, `LB` 등 마크업)를 제거하고
    수순·셋업·핵심 메타만 남긴 **정제 SGF**를 재생성.
  - `move_count`, 접바둑 셋업 돌(`AB`) 추출.
- `parsed_moves(sgf_text: str) -> list[ProMoveEntry]`
  - 정제 SGF를 프론트 `replay()`가 기대하는 좌표 형식(GTP 좌표)으로 변환.
  - 관전 상세 API 응답 시 호출.
- `clean_sgf_hash(sgf_text: str) -> str` — 정제 SGF의 sha256.

### 검증

- `board_size`가 {9, 13, 19} 중 하나여야 함.
- 본선 착수가 1수 이상이어야 함 (빈 SGF 거부).
- 파싱 실패·검증 실패 시 명확한 예외(`InvalidProSgf`)를 던진다.

## 5. 수집 경로

### 명국선 시드

- SGF 파일 위치: `backend/data/pro_games/masterpieces/*.sgf` (리포 커밋).
- 멱등 스크립트: `backend/scripts/seed_pro_games.py`
  - 디렉터리의 각 SGF를 파싱 → 정제 → `content_hash` 계산 → upsert
    (hash가 이미 있으면 스킵).
  - 깨진 SGF는 로그를 남기고 스킵, 배치는 계속.
  - 배포 시 수동 실행.
- v1 인프라(디렉터리·README·스크립트)는 구축하되, 실제 명국 SGF 파일은
  관리자가 PD 소스에서 받아 디렉터리에 넣는다. 디렉터리에 SGF가 없으면
  스크립트는 0건 적재로 정상 종료한다.

### 최근 기보 관리자 업로드

신규 파일 `backend/app/api/admin_pro.py` (admin.py 비대화 방지).

- `POST /api/admin/pro-games` — multipart SGF 업로드(단건·다건).
  파싱·정제·중복(hash) 검사 후 `collection="recent"`로 삽입.
  응답: 삽입·스킵·실패 건수와 실패 파일명.
- `GET /api/admin/pro-games` — 관리자 관리 화면용 목록.
- `DELETE /api/admin/pro-games/{id}` — 삭제.
- 모두 `AdminSession` 게이트.

## 6. 관전 API

신규 파일 `backend/app/api/spectate_pro.py`.

- `GET /api/spectate/pro` — 프로 기보 목록.
  - 쿼리: `collection`(masterpiece/recent, 선택), `q`(기사·기전 검색,
    선택), `limit`(기본 50, 최대 100).
  - 응답: 메타 행 목록 (수순 미포함).
- `GET /api/spectate/pro/{id}` — 프로 기보 상세.
  - 응답: 메타 + `sgf`에서 파싱한 수순 목록.
  - 없으면 404.
- 인증: 기존 spectate와 동일하게 `CurrentSession` (닉네임 세션 필요,
  소유권 불필요).

## 7. 프론트엔드

### `/spectate` — 탭 분리

`web/components/ui/tabs` 프리미티브로 두 탭.

- **잉크바둑 대국** — 기존 목록(진행 중·종료) 그대로.
- **프로 기보** — 명국선/최근 하위 토글, 기사·기전 검색창, 기보 카드
  목록(흑·백 기사(단)·기전·대국일·결과·판 크기).

### `/spectate/pro/[id]` — 프로 기보 재생 페이지

신규 페이지. 기존 watch 페이지(`/spectate/[id]`)의 `replay()`·`Board`·
수순 스크러버·이동 컨트롤을 재사용한다. 라이브 폴링·라이브 뱃지는 없다.

- 헤더: 흑/백 기사명(단위), 기전, 대국일, 결과.
- 프로 기사 국적 국기는 v1 미표시.

### i18n

새 문구는 `web/lib/i18n/ko.json`·`en.json`에 동시 추가.

## 8. 에러 처리

- 업로드 SGF 파싱 실패 → 422, 실패 파일명 포함.
- 시드 스크립트: 깨진 SGF 로그·스킵 후 배치 계속.
- 프로 기보 미존재 → 404 (기존 spectate 상세와 동일).
- 중복(hash 동일) 업로드 → 에러 아님, "스킵"으로 집계.

## 9. 테스트

- `backend/tests/core/test_sgf_import.py`
  - 알려진 SGF 파싱 → 메타·수순 수 검증.
  - 해설(`C[]`) 제거 확인.
  - 변화도 무시(본선만) 확인.
  - 빈 SGF·잘못된 판 크기 거부.
- `backend/tests/api/test_spectate_pro.py`
  - 목록·상세, 인증 필요(401), `collection` 필터, 검색, 404.
- `backend/tests/api/test_admin_pro.py`
  - 업로드(정상·불량 SGF), 중복 제거, 삭제, 관리자 게이트(403).
- 시드 스크립트 멱등성 테스트.

## 10. 컴포넌트 경계 요약

| 단위 | 책임 | 의존 |
|---|---|---|
| `pro_game.py` 모델 | `pro_games` 테이블 매핑 | SQLAlchemy |
| `core/sgf/import_sgf.py` | SGF 파싱·정제·메타 추출 | sgfmill |
| `seed_pro_games.py` | 명국선 SGF 멱등 적재 | import_sgf, 모델 |
| `api/admin_pro.py` | 최근 기보 업로드·관리 | import_sgf, 모델, AdminSession |
| `api/spectate_pro.py` | 프로 기보 공개 조회 | import_sgf, 모델, CurrentSession |
| `/spectate` 탭 | 잉크바둑/프로 목록 분리 | 관전 API |
| `/spectate/pro/[id]` | 프로 기보 재생 | spectate_pro API, replay(), Board |

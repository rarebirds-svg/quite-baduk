# Quality Polish Pack — 돌소리 / 계가 집표시 / Kaya 보드 테마

- **작성일**: 2026-04-26
- **상태**: 설계 승인 (사용자 OK 2026-04-26)
- **범위**: `web/` 프런트(보드 렌더·사운드·계가 다이얼로그), `backend/app/core/rules/scoring.py`·`backend/app/api/ws.py`(영역 좌표 노출), 테스트, i18n
- **트리거**: 모바일 베타 사용자 피드백 (Telegram, msg #543) — "소리가 너무 띡띡 가벼워 잘 안 들림 / 계가 점수만 나와 집계산 검증 불가 / Sabaki(<https://sabaki.yichuanshen.de/>) 같은 바둑판이 가장 예쁨, 반영 요청"
- **선행/관련 스펙**: `2026-04-20-ui-ux-uplift-design.md` (Editorial 디자인 시스템)

## 1. 목표와 배경

**목표**: 공개 베타에서 노출된 세 가지 폴리시 갭을 해결한다. 디자인 시스템(Editorial Hardcover)을 깨지 않으면서 (1) 돌 클릭 청각 피드백, (2) 계가 시 영역 시각화, (3) Sabaki 풍 사실적 보드 옵션을 제공한다.

**비목표**
- 신규 게임 기능 추가 (시간 제어, PvP, 채팅 등)
- 디자인 시스템 토큰 / 라이선스 정책 변경
- Editorial(paper) 테마의 미니멀 미학 변경 — Kaya 테마는 **추가 옵션**일 뿐 기본은 paper 유지
- 백엔드 다른 영역 스키마 변경 (게임/세션/통계)
- KataGo 어댑터·룰엔진 핵심 로직 변경 (계가 좌표 노출은 기존 `_flood_territory` 데이터 재사용일 뿐)

**성공 기준**
- 모바일 Safari/Chrome에서 돌 사운드가 "묵직한 木·石" 톤으로 들리고 음량 충분 (사용자 재확인)
- 계가 신청 후 메인 보드 위에 흑/백 영역 마커가 보이고, 사용자가 숫자와 시각 표시를 동시에 검증 가능
- `BoardBgSwitcher`에서 Kaya 선택 시 사실적 우드 텍스처 + 입체 돌 렌더링, paper 선택 시 현재 Editorial 미니멀 그대로
- 테스트: 룰엔진 100% 커버리지 유지 + 새 좌표 필드에 대한 단위 테스트 + 프런트 Board 컴포넌트 테마별 스냅샷
- 디자인 토큰 가드(`design-token-check.sh`) 통과, 새 외부 의존성 없음 (이미지 / framer-motion / 이모지 금지)

---

## 2. 기능 1: 돌 사운드 교체

### 2.1 현 상태
`web/lib/soundfx.ts`가 `AudioContext`로 1800Hz 밴드패스 화이트노이즈 70ms를 합성. 결과: "띡" 클릭음. 게인 0.35로 모바일 스피커에서 빈약. 설정 토글(`setStoneSoundEnabled`)은 이미 존재.

### 2.2 변경
- `web/public/sounds/stone-1.mp3`, `stone-2.mp3`, `stone-3.mp3` 추가 — 실제 돌이 보드에 닿는 녹음, 60–120ms, 모노, 22kHz, ~10–20KB each
- `playStoneClick()` 재작성: 풀에서 랜덤 한 개 선택, `<audio>` 엘리먼트 풀(3개) 재사용해 빠른 연속 클릭에서도 끊김 없게
- 기존 합성 fallback 제거 (Audio 엘리먼트가 모든 모던 브라우저에서 동작)
- 게인은 HTML Audio `volume = 0.7`로 노출, 사용자 향후 슬라이더 조정 여지 (이번엔 노출 X)
- 기존 enabled 토글, localStorage 키(`sfx:stone`)는 유지 (호환성)

### 2.3 음원 라이선스
**채택 기준**: CC0 또는 CC-BY 4.0 또는 MIT — 상업·재배포 무제한.

**1순위**: Sabaki <https://github.com/SabakiHQ/Sabaki> `resources/sounds/stone-*.wav` (Sabaki 본체는 MIT). 단, Sabaki 저장소의 사운드 파일이 별도 라이선스 문서를 가질 수 있으므로 `LICENSES/` 또는 README에서 사운드 라이선스 명시 확인 후 채택. 명시되지 않은 경우 2순위로 이동.

**2순위**: freesound.org `go stone`/`baduk stone`/`shogi piece` 검색 → CC0만 필터링. 후보 사전 확보 (3–5개).

**기록**: 채택한 파일의 출처·원작자·라이선스를 `web/public/sounds/CREDITS.md`에 명기 (CC-BY인 경우 표기 필수).

### 2.4 영향 / 리스크
- 번들 크기: +30–60KB (정적 자산, 코드 번들에 미포함). 무시 가능.
- iOS Safari: 사용자 첫 인터랙션 후에만 재생 가능 — 현재도 동일. 변경 없음.
- 자동 재생 정책: `<audio>` 인스턴스를 `playStoneClick()` 안에서 동기적으로 호출하므로 사용자 제스처 컨텍스트 유지.

### 2.5 테스트
- `tests/lib/soundfx.test.ts`: enabled 토글, localStorage persist, `play` 호출 횟수 mock (Audio 클래스 stub).
- 시각·청각 회귀는 수동 (모바일 + 데스크톱).

---

## 3. 기능 2: 계가 집표시

### 3.1 현 상태
- 백엔드 `app/core/rules/scoring.py`의 `_flood_territory`가 영역별 flood-fill 후 **카운트만** 반환, 좌표 폐기.
- WS `score_result` 페이로드에 `black_territory`/`white_territory` 카운트만 포함.
- 프런트 `app/game/play/[id]/page.tsx`의 계가 다이얼로그가 모달로 떠서 보드를 가리고 숫자 4줄(영역·사석·덤·합계) 표시. 사용자는 어디가 누구 집인지 검증 불가.

### 3.2 변경
**백엔드**
- `_flood_territory`가 `(black_count, white_count, black_points, white_points, dame_points)` 반환. `black_points`/`white_points`/`dame_points`: `frozenset[tuple[int, int]]`.
- `ScoreResult` 데이터클래스에 동일 3개 필드 추가 (`tuple[int, int]`의 frozenset).
- `score_game` 시그니처 그대로 유지, 좌표는 결과에 포함만.
- WS `score_result` 페이로드 (ws.py 두 곳, 자동 종국·계가 신청)에 `black_points`/`white_points`/`dame_points` 추가 — 각각 `[[x, y], ...]` 직렬화.
- 사석(`dead_stones`)도 동일하게 페이로드에 포함 → 프런트가 X 마커 렌더.

**프런트**
- `web/lib/ws.ts` `ScoreResultMsg` 타입에 4개 필드 추가.
- `Board.tsx`에 신규 prop `territoryMarkers?: { black: Pt[]; white: Pt[]; dame?: Pt[]; deadStones?: Pt[] }` 추가. SVG 오버레이로 cell 크기 18% 정사각형 (흑/백 색은 토큰 `stone-black`/`stone-white`), dame는 `ink-faint` 작은 점, 사석은 `oxblood` 얇은 X 라인.
- 계가 다이얼로그를 **shadcn `<Sheet>` (오른쪽 사이드 카드)** 로 전환. 모달 backdrop 제거 → 보드가 그대로 보임. 모바일에서는 bottom sheet (shadcn `Sheet side="bottom"`).
- 사이드 카드 내용은 현재 다이얼로그와 동일 (영역·사석·덤·합계). "닫기" 시 마커는 보드에 영구적으로 남음 (게임 종료 후이므로 후속 조작 없음).

### 3.3 데이터 흐름
1. 사용자 "계가 신청" → 기존 흐름대로 백엔드가 `score_by_request` 실행
2. `_flood_territory`가 영역 좌표를 반환 → `score_game`이 `ScoreResult` 구성
3. WS `score_result` 메시지 (좌표 포함) 송신
4. 프런트 reducer가 `scoringDetail`에 저장 → `Board.tsx`에 `territoryMarkers` prop 전달 + Sheet 오픈

### 3.4 영향 / 리스크
- 페이로드 크기: 19×19 보드 최악의 경우 한 색당 200점 가량 좌표 → JSON ~3KB. WS에서 1회성. 허용.
- 룰엔진 100% 커버리지 유지: 새 필드에 대한 테스트 추가 (정확한 좌표 셋 비교).
- shadcn `Sheet` 의존성 신규 — 디자인 시스템 §컴포넌트 구조에서 허용된 shadcn 프리미티브 목록에 이미 명시되어 있으므로 신규 외부 의존성 아님 (라이브러리 가드 위반 없음).

### 3.5 테스트
- `backend/tests/rules/test_scoring.py`: 좌표 셋 정확성 (단순 보드 + 사석 케이스 포함).
- `web/tests/board.test.ts`: territoryMarkers prop으로 마커가 SVG에 렌더되는지.
- 수동 시나리오: 양보 → 자동 계가 → 보드 위 마커 보이는지 / 계가 신청 → 동일.

---

## 4. 기능 3: Kaya 테마 폴리싱

### 4.1 현 상태
`web/store/boardThemeStore.ts`에 `BoardTheme` = `'paper' | 'wood' | 'slate' | 'kaya'` 정의. 각 테마는 `bg`/`lineInk`/`starInk`/`labelInk` 4색만 보유. 현재 Board는 `palette.bg`로 단순 단색 배경, 돌은 모든 테마에서 평면 원. → Sabaki 같은 사실감 부재.

### 4.2 변경 — 테마별 시각 분기 도입

`BOARD_THEMES` 항목에 **렌더 힌트** 필드 추가:
```ts
type BoardThemeMeta = {
  bg: string; lineInk: string; starInk: string; labelInk: string;
  surface: 'flat' | 'wood';     // 배경 텍스처 종류
  stoneStyle: 'flat' | 'lithic'; // 돌 렌더 방식
  shadow: boolean;               // 돌 drop-shadow
};
```
- `paper` → flat / flat / no shadow (Editorial 미니멀, 변경 없음)
- `wood`, `kaya` → wood / lithic / shadow
- `slate` → flat / lithic / shadow (어두운 평면 + 입체 돌)

### 4.3 우드 텍스처 — 이미지 의존 X
`Board.tsx` SVG 안에 inline `<defs><filter>` 정의:
```xml
<filter id="kayaGrain">
  <feTurbulence type="fractalNoise" baseFrequency="0.012 0.6" numOctaves="2" seed="7"/>
  <feColorMatrix values="0 0 0 0 0.55  0 0 0 0 0.38  0 0 0 0 0.20  0 0 0 0.10 0"/>
  <feComposite in2="SourceGraphic" operator="in"/>
</filter>
```
+ 동심 라디얼 그라디언트 (밝은 중앙 → 어두운 가장자리)로 광원 효과. 모두 SVG/CSS, 외부 이미지 0.

`palette.surface === 'wood'`일 때 `<rect ...filter="url(#kayaGrain)"/>` 위에 그리드선·돌 렌더.

### 4.4 입체 돌 — `stoneStyle === 'lithic'`
`<defs>`에 라디얼 그라디언트 2종:
- `stoneBlackLithic`: 중심 → 가장자리 (`#3a342f` → `#0a0807`), 우상단 11° 위치에 작은 흰 하이라이트 (alpha 0.18)
- `stoneWhiteLithic`: 중심 → 가장자리 (`#fbfaf6` → `#bbb5a8`), 좌하단에 부드러운 그늘

돌 `<circle>` `fill={isLithic ? "url(#stoneBlackLithic)" : tokens.stone-black}`. 토큰 색은 그라디언트의 stop 값으로 흡수 (하드코딩 hex 회피하려면 `boardThemeStore`에 stop 값 토큰 필드 추가).

### 4.5 그림자
`palette.shadow === true`일 때 돌 아래 `<ellipse>` 작은 드롭 (cx, cy + 0.5, rx 0.4*CELL, ry 0.12*CELL, fill `rgba(0,0,0,0.18)`). 디자인 시스템은 카드/UI에서 그림자를 금지하지만 **3D 돌의 사실감 표현은 보드 시각 옵션**이므로 정책 예외 (Kaya/wood/slate 한정, paper는 그대로 평면). spec에 명문화.

### 4.6 영향 / 리스크
- paper(기본) 테마 사용자에게 **시각 변경 0**.
- SVG `<filter>` 모바일 Safari 성능: `feTurbulence` cost 있음 — `<rect>` 1회 렌더이므로 9×9~19×19 보드에서 무시할 수준 (측정 후 확인).
- 다크 모드: `slate`는 어두운 톤 그대로, `kaya`/`wood`는 라이트만 가정 (다크 모드에선 전체 페이지가 어두워지지만 보드는 따뜻한 톤 유지 — 의도된 콘트라스트).
- 디자인 시스템 §그림자 정책에 보드 한정 예외 1개 추가 필요 → CLAUDE.md 한 줄 갱신.

### 4.7 테스트
- `web/tests/board.test.ts`: 테마별 prop 변경 시 SVG `filter`/`fill` 속성 분기 확인.
- 시각 회귀: Playwright `visual-qa` 에이전트로 4개 테마 × 라이트/다크 스크린샷 (paper 라이트는 기존 baseline 유지).

---

## 5. 작업 단위 요약

| # | 영역 | 파일 | 추정 |
|---|---|---|---|
| 1 | 백엔드 | `core/rules/scoring.py` (좌표 반환), `tests/rules/test_scoring.py` | S |
| 2 | 백엔드 | `api/ws.py` (페이로드 두 곳) | XS |
| 3 | 프런트 | `lib/ws.ts` 타입, `app/game/play/[id]/page.tsx` (Sheet 전환) | S |
| 4 | 프런트 | `components/Board.tsx` territoryMarkers prop + 테마 분기 (filter, lithic, shadow) | M |
| 5 | 프런트 | `store/boardThemeStore.ts` (메타 필드 추가) | XS |
| 6 | 자산 | `public/sounds/stone-{1,2,3}.mp3`, `CREDITS.md`, `lib/soundfx.ts` 재작성 | S |
| 7 | 테스트 | rules·board·soundfx 추가 | S |
| 8 | 디자인 시스템 | CLAUDE.md §Radius/Shadow에 보드 예외 1줄 | XS |

---

## 6. 결정된 사항 / 미결 사항

**결정 (사용자 OK)**
- 보드 방향: C — 멀티 테마, Editorial 기본 + Kaya 폴리싱 추가 옵션
- 사운드: 실제 샘플 3개 랜덤, CC0/MIT만
- 계가: 보드 위 마커 + Sheet 사이드/바텀 카드 (모달 제거)

**미결 (구현 단계에서 결정)**
- 사운드 음원의 정확한 출처 — Sabaki 우선 시도, 라이선스 미명시면 freesound CC0
- Kaya 우드 그레인의 색상 stop 값 미세 튜닝 — 시각 QA 에이전트 결과 보고 반복

---

## 7. 참고

- 사용자 피드백 원문: Telegram msg #543 (2026-04-25 22:17 KST)
- Sabaki: <https://github.com/SabakiHQ/Sabaki> (MIT)
- 디자인 시스템 정책: `CLAUDE.md` §UI/UX 디자인 시스템 규칙
- 기존 보드 구현: `web/components/Board.tsx`
- 기존 룰엔진: `backend/app/core/rules/scoring.py`

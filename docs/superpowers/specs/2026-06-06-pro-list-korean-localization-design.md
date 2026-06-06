# 프로 기보 목록 한국어 표기 (기사명·기전명·단) 설계

작성일. 2026-06-06
상태. 설계 승인 완료

## 배경

프로 기보 목록(`/spectate/pro`)의 명국·세계기전·최근 탭에서 기사명·기전명·단이 모두 영어(SGF 원문 로마자)로 표기된다. 예: `Honinbo Dosaku`, `Shibano Toramaru vs Ichiriki Ryo · 32nd Agon-Kiriyama Cup`. 한국어 모드에서는 한글로 보여준다. 영어 모드는 국제 표준 영문 원문을 유지한다.

직전 작업에서 세계기전 6대 컵의 기전명·국수는 이미 `formatProEvent`로 한글화됐다. 이 작업은 그 범위를 **기사명 + 전체 기전명 + 단**으로 확장한다.

## 데이터 규모 (DB 실측, cwi 200국 포함)

- 고유 기사명 **249**개 (한·중·일, 고전~현대).
- 고유 기전 base **23**종 (6대 세계기전 + ACOM Cup·Agon-Kiriyama Cup·Aizu Cup·Castle Game·All-Japan·AlphaGo selfplay/test·Future of Go Summit·Google DeepMind·10/20/30-game match·Teaching game·Mission from Ryukyu Islands 등).
- 단 필드는 비정형: `9p`, `7d`, `9p, Kisei`, `2p, Women's Kisei`, `9p, Kisei, Judan, Oza` 등 — 선행 단 토큰 + 타이틀 접미가 섞임.

## 목표 / 비목표

- **목표**: ko 모드에서 기사명·기전명·단을 한글로. 매핑 없는 항목은 영문 폴백.
- **비목표**: en 모드 변경(영문 원문 유지). 백엔드/DB 변경. 타이틀(Kisei/Honinbo 등) 자체의 한글화(단 표기에서 접미는 생략).
- 매핑 데이터는 모델이 생성하되 `korean-copy-qa` 에이전트로 검증하고, 확신 없는 항목은 누락(영문 폴백)한다.

## 아키텍처

ko 전용 단방향 참조 맵을 데이터 모듈에 두고, 렌더 시 헬퍼로 변환한다. en은 원문이므로 맵 불필요.

### `web/lib/proLocale.ts` (신규)

```
PLAYER_KO: Record<string, string>      // 영문 기사명 → 한글 (249, 불확실 누락)
TOURNAMENT_KO: Record<string, string>  // 영문 기전 base → 한글 (23)
localizePlayer(name: string, locale: Locale): string
localizeRank(rank: string | null, locale: Locale): string
```
- `localizePlayer` — locale==='ko' && PLAYER_KO[name] 있으면 그 값, 아니면 `name`. ko 외 로케일은 항상 `name`.
- `localizeRank` — locale!=='ko' 또는 falsy면 `rank ?? ""`. ko면 `rank`의 선행 토큰을 정규식 `^\s*(\d+)\s*[pdPD]\b`로 잡아 `"{n}단"` 반환. 매칭 실패(예: 비표준)면 원문 `rank`. 타이틀 접미(`, Kisei` 등)는 결과에 포함하지 않는다.
  - 예: `"9p"`→`"9단"`, `"9p, Kisei, Judan, Oza"`→`"9단"`, `"7d"`→`"7단"`, `""`/`null`→`""`.

### `web/lib/proEvent.ts` (수정 — 일반화)

기존 `formatProEvent`는 `…\s+Cup(?:\s+Final)?…` 정규식으로 6대 컵만 처리한다. 이를 base 사전 조회 방식으로 일반화한다.

- 파싱: `event`에서 선행 서수 `^(\d+)(?:st|nd|rd|th)\s+` → `editionNum`(없으면 생략). 남은 문자열에서 후행 ` Final`/` Title`/`, …preliminary…`를 분리해 `stage`(final/prelim/없음) 판정, 나머지를 `base`로.
- 기전명: `TOURNAMENT_KO[base]` 조회.
  - ko & base 매칭: `[제{edition}회] {TOURNAMENT_KO[base]} [{결승/예선}] [제{gameNo}국]` (없는 조각 생략, 기존 i18n 템플릿 `spectate.proEdition/proGameNo/proStage` 재사용).
  - 미매칭(base 없음) 또는 ko 외: **원문 `event`** 반환 + 국수만 로케일 접미(ko `제N국`, en `· Game N`) — 현행 폴백 동작 유지.
- `RO`(round) 국수 파싱은 현행 `parseGameNo` 유지.
- 기존 6대 컵은 `TOURNAMENT_KO`에 포함되므로 기존 `formatProEvent` 출력(예: `제10회 춘란배 결승 제3국`)이 동일하게 유지된다 — 회귀 테스트로 보장.

### 컴포넌트

- `web/components/ProGameList.tsx` — `{r.black_player}`/`{r.white_player}` → `localizePlayer(…, locale)`, `{r.black_rank}`/`{r.white_rank}` → `localizeRank(…, locale)`. event는 기존 `formatProEvent`.
- `web/app/spectate/pro/[id]/page.tsx` — `blackLabel`/`whiteLabel` 조립 시 `localizePlayer`·`localizeRank` 적용.

### i18n 정리

`formatProEvent`가 기전명을 `TOURNAMENT_KO`(데이터 모듈)에서 조회하므로 기존 `spectate.proTournament.{chunlan,…}` 6키는 미사용 → ko.json·en.json에서 제거. 소형 템플릿 `proEdition`·`proGameNo`·`proStage`는 유지.

## 데이터 생성·검증 절차

1. 백엔드에서 고유 기사명·기전 base를 추출(스크립트 1회 조회) → 구현자가 `PLAYER_KO`/`TOURNAMENT_KO` 초안 작성. 확신 없는 항목은 **넣지 않는다**(영문 폴백).
2. `korean-copy-qa` 에이전트로 생성 맵을 검증 — 오표기·일관성(한·중·일 표기 관례: 한국 기사 한글명, 일본 기사 한글 음차, 중국 기사 한자 독음 또는 통용 표기) 점검, 의심 항목은 제거(폴백) 권고.
3. QA 반영 후 확정.

표기 관례 가이드(QA 기준).
- 한국 기사: 통용 한글명(예: Lee Changho→이창호, Cho Hunhyun→조훈현, Shin Jinseo→신진서).
- 일본 기사: 한글 음차(예: Honinbo Dosaku→혼인보 도사쿠, Cho Chikun→조치훈, Iyama Yuta→이야마 유타).
- 중국 기사: 통용 표기(예: Ke Jie→커제, Gu Li→구리, Chang Hao→창하오).
- 불확실하면 누락(영문 폴백) — 틀린 한글보다 영문이 낫다.

## 테스트

- **vitest `web/tests/proLocale.test.ts` (신규)**:
  - `localizePlayer`: 매핑 존재(ko)→한글, 미매핑(ko)→원문, en→원문.
  - `localizeRank`: `9p`→`9단`, `"9p, Kisei, Judan, Oza"`→`9단`, `7d`→`7단`, `null`→`""`, en→원문, 비표준(`"insei"`)→원문.
- **vitest `web/tests/proEvent.test.ts` (확장)**: 기존 6대 컵 출력 유지(회귀) + 신규 base(예: `Castle Game`→ko 한글, `32nd Agon-Kiriyama Cup`→`제32회 …배 …`) + 미매핑 base→원문 폴백.
- **korean-copy-qa**: 생성된 `PLAYER_KO`/`TOURNAMENT_KO` 자연스러움·일관성 검증(코드 테스트 아님, 에이전트 리뷰).

## 영향 / 배포

- 프론트 전용. DB·API 변경 없음. en 모드 무변경.
- 배포 시 web 재빌드 + `com.baduk.web` 재시작 필요(포매터·데이터는 빌드 산출물).
- 매핑 누락분은 영문으로 안전하게 표시되며, 추후 항목 추가로 점진 개선 가능.

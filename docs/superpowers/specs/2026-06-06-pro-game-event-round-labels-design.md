# 프로 기보 리스트 — 기전명·단계·국수 표기 (로케일 인식)

작성일. 2026-06-06
상태. 설계 승인 완료 (A안 — 하이브리드)

## 배경

프로 기보 리스트(`/spectate/pro`)는 현재 SGF의 `EV` 원문(영어, 예: "10th Chunlan Cup
Final")을 그대로 한 줄로 노출한다. 요구사항은 기전명·단계·국수를 표기하되, **한국어 모드에서는
한국어로** 보여주는 것이다 (예: "제10회 춘란배 결승 제3국").

## 데이터 현실

- **world 컬렉션(286국)**: 전부 `EV`·`RO` 보유. 이 컬렉션 자체가 세계기전 결승 모음이라
  "단계"는 사실상 전부 결승이고, `RO`는 단계가 아니라 결승 best-of-N 중 **제N국**이다.
- **masterpiece 컬렉션(625국)**: 102국만 `EV` 보유, 대부분 `RO` 없음(옛 기보).
- 시드에 "준결승·4강·8강" 같은 다양한 단계는 사실상 없다.

### EV 형식 (일관적)

```
{서수} {기전} Cup[ Final][, Korean preliminary]
예: "10th Chunlan Cup Final", "10th Fujitsu Cup", "Ing Cup, Korean preliminary"
```

기전 6종. Chunlan / Fujitsu / Ing / LG / Samsung / Toyota.
"Final" 접미사는 LG·Samsung·Chunlan·Toyota엔 있고 Fujitsu·Ing엔 없다(그래도 결승).

### RO 형식

`"1"`~`"5"`, `"Final 1"`~`"Final 5"`, `"Final"`, `"final"`. 즉 후행 정수가 국수.
정수가 없으면(단순 "Final") 국수 없음.

## 접근법 (A안 — 하이브리드)

백엔드는 RO 원문을 `round` 컬럼 1개로만 저장한다. 표기용 파싱·매핑·로컬라이즈는 프론트
포매터가 담당한다. 기전이 6종으로 안정적이고 미매칭 시 원문 fallback이 가능해 컬럼 4개로
구조화하는 B안보다 단순하다(YAGNI).

데이터 흐름.
```
SGF RO → ParsedProGame.round → pro_games.round(DB) → API round 필드
       → 프론트 formatProEvent(event, round, locale) → "제10회 춘란배 결승 제3국"
```

## 컴포넌트별 설계

### 백엔드

1. **`backend/app/core/sgf/import_sgf.py`**
   - `_opt("RO")`로 RO 파싱 → `ParsedProGame.round: str | None` 추가.
   - **`_build_clean_sgf`는 변경하지 않는다** (RO를 clean_sgf에 넣지 않음) → content_hash 불변
     → 기존 행 backfill이 깔끔한 UPDATE로 성립.

2. **마이그레이션** `00NN_pro_game_round.py`
   - `pro_games`에 `round` 컬럼(`sa.String(32)`, nullable) 추가. downgrade는 drop.

3. **`backend/app/models/pro_game.py`**
   - `round: Mapped[str | None]` 컬럼 + `from_parsed`에 `round=parsed.round` 반영.

4. **Backfill** — `backend/scripts/seed_pro_games.py`
   - content_hash가 이미 있을 때 skip하던 분기를, `round`가 비어 있으면 해당 행을 UPDATE하도록
     보강(있는 데이터 보존, round만 채움). world+masterpiece 양쪽 재실행으로 286+85국 backfill.
   - 신규 적재 경로는 기존대로 `round` 포함해 insert.

5. **`backend/app/api/spectate_pro.py`** + 스키마
   - 리스트(`/api/spectate/pro`)·상세(`/api/spectate/pro/{id}`) 응답 dict에 `"round": g.round` 추가.
   - 응답 스키마(현 `event: str | None` 인근)에 `round: str | None` 추가.

### 프론트

6. **`web/lib/proEvent.ts`** (신규)
   - `parseProEvent(event)`: EV→`{edition?: number, tournamentKey?: string, stage?: 'final'|'prelim'}`.
     - 정규식: `^(?:(\d+)(?:st|nd|rd|th)\s+)?(.+?)\s+Cup(?:\s+Final)?(?:,\s*(.+))?$`
     - tournamentKey: 이름 소문자 매핑(chunlan/fujitsu/ing/lg/samsung/toyota). 미매칭 → undefined.
     - stage: EV에 "preliminary" 포함 → `prelim`; EV에 "Final" 포함 또는 round에 국수 있음 →
       `final`; 그 외 → undefined(단계 미표시). 국수 존재는 결승 best-of 시리즈를 함의하므로 안전.
   - `parseRound(round)`: 후행 정수 추출 → `gameNo?: number`.
   - `formatProEvent(event, round, locale, t)`: `t`는 i18n 번역 함수, `locale`은 현재 로케일.
     - 미매칭(tournamentKey 없음) → **원문 event 반환**(graceful fallback). round의 gameNo는
       로케일에 맞게 덧붙임(ko: "제N국", en: "· Game N").
     - ko: `[제{edition}회 ]{기전라벨}[ {단계라벨}][ 제{gameNo}국]` (없는 조각 생략).
     - en: 원문 event + (gameNo ? ` · Game {N}` : ''). 영어는 국제 표준 영문 유지(직전 합의).

7. **i18n** — `web/lib/i18n/ko.json` · `en.json` 동시 추가.
   - `spectate.pro.tournament.{chunlan,fujitsu,ing,lg,samsung,toyota}`
     - ko: 춘란배 / 후지쯔배 / 응씨배 / LG배 / 삼성화재배 / 도요타배
     - en: Chunlan Cup / Fujitsu Cup / Ing Cup / LG Cup / Samsung Cup / Toyota Cup (영어는 사실상
       원문 유지이지만 키 일관성 위해 등록)
   - `spectate.pro.stage.{final,prelim}` — ko: 결승 / 예선, en: Final / Preliminary.

8. **`web/components/ProGameList.tsx`** (+ 프로 상세 `web/app/spectate/pro/[id]/page.tsx`)
   - 행 타입에 `round: string | null` 추가.
   - `{r.event && <span>{r.event}</span>}` → `formatProEvent(r.event, r.round, locale, t)` 결과 렌더
     (빈 문자열이면 미표시).

## 로컬라이즈 예시

| event(원문) | round | ko | en |
|---|---|---|---|
| 10th Chunlan Cup Final | Final 3 | 제10회 춘란배 결승 제3국 | 10th Chunlan Cup Final · Game 3 |
| 5th Samsung Cup Final | 1 | 제5회 삼성화재배 결승 제1국 | 5th Samsung Cup Final · Game 1 |
| 10th Ing Cup | 2 | 제10회 응씨배 결승 제2국 | 10th Ing Cup · Game 2 |
| Ing Cup, Korean preliminary | (없음) | 응씨배 예선 | Ing Cup, Korean preliminary |
| (미지 기전) | 1 | (원문) 제1국 | (원문) · Game 1 |
| (event 없음) | — | (미표시) | (미표시) |

## 엣지 케이스

- event 없는 masterpiece 523국 → 현행처럼 미표시.
- 미지 기전명 → 원문 노출(파싱 실패해도 정보 손실 없음).
- RO에 국수 없음(단순 "Final") → 제N국 생략.
- edition 없음(EV에 서수 없음) → 제N회 생략.

## 테스트

- **백엔드**(`tests/`의 pro SGF 파싱 테스트): RO 파싱 단위 — "3", "Final 3", "Final", RO 없음.
  content_hash가 backfill 전후 동일함을 확인하는 테스트(회귀 방지).
- **프론트**(vitest, `web/tests/proEvent.test.ts` 신규): `formatProEvent` ko·en 각각 —
  표의 모든 행 + 미지 기전 fallback + RO 변종 + event null.

## 비범위

- 영어 UI를 한국식 로마자로 바꾸지 않음(국제 표준 유지).
- SGF `KM`/`RO` 등 파일 표준 속성명 변경 없음.
- B안(tournament/edition/stage/game_no 구조화 컬럼) 도입 안 함.
- clean_sgf에 RO 추가 안 함(content_hash 안정성 우선).

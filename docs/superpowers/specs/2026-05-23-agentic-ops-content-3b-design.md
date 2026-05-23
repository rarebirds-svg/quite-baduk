# Agentic Ops — 하위 프로젝트 3b: 테마 + 이 달의 명국

- 작성일: 2026-05-23
- 상태: 설계 승인 완료, 구현 계획 대기
- 의존: 하위 프로젝트 3a (콘텐츠 수집·SEO 인덱스)
- 범위: inkbaduk 프로기보의 **종합 테마 페이지 + 월간 픽** 큐레이션

## 배경

3a가 911개 프로기보를 sitemap·메타로 검색 노출 가능하게 만들었다. 다만 각 게임은
독립된 페이지로만 존재해 "이세돌 명국 모음", "본인방전 역사" 같은 묶음 검색에는
약하다. 3b는 그 묶음(테마 페이지)과 결정적 자동 픽(이 달의 명국)을 추가해 SEO
밀도와 사용자 탐색을 키운다.

### 현재 상태 (조사 확정)

- `pro_games` 스키마에 `collection`, `event`, `game_date` 같은 필터 가능한 필드 풍부.
  911국 중 388국이 `event` 태그 있음.
- 컬렉션 구성 — `masterpiece`, `world`, `cwi` 등 다양.
- 사용자 결정 — **자동 알고리즘**(LLM·사람 큐레이션 배제). 결정적·재현 가능해야 한다.

### 결정된 설계 축

- **테마 카탈로그**: 정적 상수 5-8개 (코드 상수, DB 테이블 아님). 큐레이션 운영 부담 0.
- **월간 픽**: 결정적 해시 시드. 한 달 내 같은 답.
- **주간 픽 제외** — 911 ÷ 52 = 17년 1순환이라 SEO 효과 작고 노이즈 큼.

## 접근 — A (정적 카탈로그 + 결정적 픽)

- A. 정적 카탈로그 + 결정적 픽 (채택) — 코드 상수 + DB 필터. 새 인프라 0, 검증 쉬움.
- B. DB 테이블 + admin UI — themes/picks DB row + 관리 UI. 큐레이션 운영 부담.
- C. LLM 자동 큐레이션 — 자동 알고리즘 결정과 충돌. 3c 영역.

## 설계

### 섹션 1 — 테마 카탈로그 + 필터 API + 페이지

**`web/lib/pro-themes.ts`**: `{slug, label, description, filter}[]` 정적 상수 5-8개.

초기 테마 — 데이터가 실재하는 것만:

| slug | label | filter |
|---|---|---|
| `masterpieces` | 명국선 | `collection='masterpiece'` |
| `world-finals` | 세계기전 결승 | `collection='world'` |
| `cwi` | CWI 공개기보 | `collection='cwi'` |
| `honinbo` | 본인방전 | `event LIKE '%Honinbo%'` |
| `castle-games` | 오성 (御城碁) | `event='Castle Game'` |
| `21st-century` | 21세기 명국 | `game_date >= '2000-01-01'` |

backend `/api/spectate/pro/theme/<slug>` — slug → filter 매핑은 backend에 하드코드.
알 수 없는 slug는 404. 현재 응답은 전체 게임 목록(테마당 최대 ~625)을 한 번에
반환 — 페이지네이션은 deferred(데이터 작아 즉시 필요 없음, 후속에서 limit/offset 추가).

web `app/spectate/themes/[slug]/page.tsx` — 서버 컴포넌트, 게임 목록 페이지네이션,
`generateMetadata`로 라벨·설명·canonical.

### 섹션 2 — 이 달의 명국

**결정적 알고리즘** (한 달 내 같은 답 보장):

1. 입력 `YYYY-MM`. `MM` 추출.
2. `SELECT id FROM pro_games WHERE strftime('%m', game_date) = '<MM>'`로 후보.
3. `collection='masterpiece'` 후보 우선; 없으면 전체.
4. `sha256('YYYY-MM').int % len(candidates)`로 단일 선택.
5. 결과 게임 반환.

candidates 없는 달은 fallback — 같은 알고리즘을 `collection='masterpiece'` 강제로 다시
시도, 그래도 없으면 random pro_games 1국 (혹은 그달의 인덱스 페이지 404).

backend `/api/spectate/pro/pick/monthly/<YYYY-MM>` → 단일 game 메타+id.

web:
- `app/spectate/picks/monthly/[yyyymm]/page.tsx` — 픽 랜딩 (게임 정보·관전 링크·이전·다음 달).
- `app/spectate/picks/page.tsx` — 최근 12개월 + 현재 + 향후 1개월 픽 리스트.

### 섹션 3 — sitemap·메타 통합

3a의 `web/app/sitemap.ts` 확장:
- 테마: `/spectate/themes/<slug>` × 5-8.
- 픽: `/spectate/picks/` + `/spectate/picks/monthly/<YYYY-MM>` × (최근 12개월 + 현재 + 향후 1개월 = ~14).

각 페이지에 `generateMetadata` — 테마는 라벨·설명·게임 수, 픽은 게임 정보 + "YYYY년 M월
이 달의 명국". OG·canonical 포함.

### 섹션 4 — 범위 경계

**포함** — 테마 카탈로그 5-8개 + 필터 API + 테마 페이지, 월간 픽 API + 픽 페이지 +
인덱스, sitemap·메타 통합, 결정적 알고리즘.

**제외** — 주간 픽(deferred), 테마 관리 admin UI, LLM 자동 큐레이션(3c), AI 게임
해설 텍스트(3c), 이미지 OG 보드 렌더(별도), `theme_detail` 페이지네이션(deferred —
현재 데이터 크기로 무난).

## 검증 기준

이 4가지가 실제 명령 실행으로 통과하면 하위 프로젝트 3b 완료. 문서만으로 완료 선언 금지.

1. 테마 카탈로그 5+ 정의됨. 각 `/spectate/themes/<slug>` 200 응답 + 필터 결과(실제 DB 카운트)
   합치.
2. `/spectate/picks/monthly/<현재 YYYY-MM>` 200 + 결정적 단일 게임. 같은 입력 두 번 호출
   시 같은 게임. 다른 YYYY-MM은 다른 게임(또는 같은 후보 풀에서 다른 인덱스).
3. sitemap.xml에 911(프로) + 5+(테마) + 14(픽) URL 전부 포함.
4. 각 새 페이지가 `generateMetadata`로 고유 title·canonical·OG.

## 리스크와 완화

| 리스크 | 완화 |
|---|---|
| 알고리즘이 모든 달에 후보 0 → 404 양산 | `collection='masterpiece'` fallback, 그래도 없으면 픽 페이지를 sitemap에서 제외 |
| 테마 필터 결과 0개로 빈 페이지 | 테마 카탈로그 등록 전 데이터 확인 — 빈 테마는 등록 안 함 |
| 테마 slug 변경 시 검색 노출 손실 | slug는 한 번 정하면 변경 금지(canonical), 라벨만 갱신 |
| 픽 알고리즘 변경으로 매월 답 바뀜 | 알고리즘 함수에 버전 주석 — 변경 시 검색 노출 영향 인지 |

## 다음 단계

이 spec 승인 후 `writing-plans` 스킬로 하위 프로젝트 3b의 구현 계획을 작성한다.
3c(FAQ·용어 해설 LLM 콘텐츠), sub-project 4(지원·분석팀)는 별도 사이클.

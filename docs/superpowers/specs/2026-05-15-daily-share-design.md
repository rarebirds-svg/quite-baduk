# 일일 챌린지 결과 공유 설계서

- **작성일**: 2026-05-15
- **프로젝트 경로**: `/Users/daegong/projects/baduk/`
- **상태**: 초안 (사용자 검토 대기)

## 1. 배경과 목적

일일 챌린지를 푼 직후의 성취감을 외부 채널(카카오톡·트위터·디스코드 등)로 옮길 수 있는 경로가 현재 없다. SGF 다운로드는 가능하지만 *완료한 한 문제의 결과* 를 손쉽게 자랑·공유할 수단이 부재하다.

본 기능은 다음을 목표로 한다.

- 채점 직후 결과 패널에서 1탭으로 공유 시작.
- 받는 사람이 메시지 앱에서 카드 형태 미리보기(og:image)로 확인.
- 링크 클릭 시 같은 문제를 *직접 풀어보도록* 유도 → 자연스러운 유입 경로.
- 스포일러 방지(답수 비공개) — 받는 사람이 동일한 도전을 받을 수 있어야 함.

비목표(v1 제외)

- 누적 streak / 일별 집계 / 리더보드.
- 다중 문제 묶음 공유(워들식).
- 카카오 SDK 직접 연동(웹 표준 og:image로 충분).
- 결과 위변조 방지를 위한 서명 토큰.

## 2. 사용자 시나리오

1. 사용자가 일일 챌린지에서 문제를 풀고 `verdict=best` 결과를 받음.
2. 결과 패널 하단 **공유** 버튼을 누름.
3. 모바일(iOS/Android): 시스템 공유 시트가 열리고 카톡·메시지·트위터 등 어디로든 보낼 수 있음.
   - 데스크탑(Chrome 등 Web Share 미지원): 링크가 클립보드로 복사되고 "복사되었습니다" 토스트.
4. 받는 사람이 카톡에서 링크를 보면 카드 미리보기(보드·verdict·브랜드)가 자동 표시.
5. 클릭 시 `/daily/share/[id]` 랜딩 페이지 → 같은 보드 위치 + 친구의 verdict 배지 + "직접 풀어보기" CTA.
6. "직접 풀어보기" → `/daily?challenge=[id]`로 이동, 같은 문제로 일일 챌린지 시작.

## 3. 화면 설계

### 3.1 결과 패널 변경 (`/daily`)

기존 verdict 박스 아래에 한 줄로 **공유** 버튼 추가. 다른 결과 정보(승률, top moves) 위치는 그대로.

### 3.2 OG 이미지 (1200×630)

```
┌──────────────────────────────────────────┐
│ 조용한 승부 · 일일 챌린지                │
│                                          │
│   ┌──────────────────┐    사활 · 중급    │
│   │ ● ○ . . . . . .  │   ─────────       │
│   │ . ● ○ . . . . .  │   최선의 한 수    │  ← verdict 배지
│   │ . . ● ○ . . . .  │   97% → 99%       │  ← 승률 변화(있을 때만)
│   │  (퍼즐 위치만)   │                   │
│   └──────────────────┘                   │
│                                          │
│  k-baduk.com           직접 풀어보기 →   │
└──────────────────────────────────────────┘
```

- **답수 표시 안 함** — `challenge.setup`만 그림.
- verdict별 배지 색상:
  - `best` → moss
  - `ok` → ink
  - `weak` → ink-mute
  - `miss` → oxblood
  - 없음(verdict 미전달) → 배지 자체 미표시, generic "일일 챌린지" 카드.
- 폰트: Newsreader(서브타이틀) + Pretendard(본문) — `next/og`가 fetch한 woff 폰트 임베드.

### 3.3 공유 랜딩 페이지 (`/daily/share/[id]`)

- 헤더: "친구의 도전" + 친구의 verdict 배지 (스포일러 없음).
- 본문: `StaticBoardSVG`로 setup만 렌더.
- CTA: "직접 풀어보기" → `/daily?challenge=[id]`.
- 잘못된 ID → 404 메시지 + "오늘의 챌린지 가기" 링크.

## 4. 아키텍처

### 4.1 백엔드

신규 엔드포인트 한 개.

```
GET /api/daily-challenge/{id}
  200 → _serialise(challenge)
  404 → {"detail": "challenge_not_found"}
```

- 기존 `app.services.daily_challenge.get_by_id`를 그대로 사용.
- 기존 endpoint들과 동일하게 `CurrentSession` 의존(익명 세션 자동 발급).
- 기존 `rate_limiter`와 동일한 limit 부여(과도한 og 이미지 fetch 방지).

### 4.2 프론트엔드

**신규 파일**

- `web/components/daily/ShareButton.tsx`
  - props: `{ challengeId, verdict, topic, difficulty }`
  - `navigator.share()` 우선, 미지원 시 클립보드 + 토스트.
  - aria-label 포함.

- `web/components/daily/StaticBoardSVG.tsx`
  - props: `{ boardSize, setup, width?, height? }`
  - 보드선·별점·돌 원형만. 상호작용 없음.
  - 랜딩 페이지·OG 라우트가 공유.

- `web/app/daily/share/[id]/page.tsx`
  - 서버 컴포넌트. 백엔드에서 challenge fetch.
  - `generateMetadata`로 og:image, og:title, og:description 설정.
  - 본문 렌더(`StaticBoardSVG` + verdict 배지 + CTA).

- `web/app/api/og/daily/[id]/route.tsx`
  - `next/og`의 `ImageResponse`로 1200×630 PNG 생성.
  - 쿼리: `?v=best|ok|weak|miss`, `?topic=...`, `?diff=...` (생략 가능).
  - 보드는 인라인 SVG로 직접 작성(Satori SVG 호환).

**변경 파일**

- `web/app/daily/page.tsx`
  - 결과 패널에 `<ShareButton>` 한 줄 추가.
  - URL 파라미터 `?challenge=[id]`가 있으면 random 대신 해당 ID로 fetch하는 분기 추가.

- `web/lib/i18n/ko.json`, `web/lib/i18n/en.json`
  - 신규 키 (대략 8개):
    - `daily.share.button` "공유" / "Share"
    - `daily.share.title` "조용한 승부 · 일일 챌린지" / "K-Baduk · Daily Challenge"
    - `daily.share.copied` "링크가 복사되었습니다" / "Link copied"
    - `daily.share.shareFailed` "공유에 실패했습니다" / "Could not share"
    - `daily.share.tryIt` "직접 풀어보기" / "Try this puzzle"
    - `daily.share.byFriend` "친구의 도전" / "A friend's challenge"
    - `daily.share.notFound` "문제를 찾을 수 없습니다" / "Puzzle not found"
    - `daily.share.goToDaily` "오늘의 챌린지 가기" / "Go to today's challenge"

### 4.3 데이터 흐름

```
사용자 채점 결과 → 공유 클릭
  │
  ▼
ShareButton.handleClick():
  url = `${origin}/daily/share/${challengeId}?v=${verdict}`
  text = `${topicLabel} · ${diffLabel} — ${verdictLabel}`
  if (navigator.share) await navigator.share({ url, title, text })
  else { clipboard.writeText(url); toast.success(copied) }

받는 사람 클릭
  │
  ▼  Next.js 서버 컴포넌트
share/[id]/page.tsx (SSR):
  challenge = await fetch(`/api/daily-challenge/${id}`)
  generateMetadata → og:image = `/api/og/daily/${id}?v=...&topic=...&diff=...`
  본문 렌더(StaticBoardSVG + 배지 + CTA)

og:image 라우트
  │
  ▼
/api/og/daily/[id]/route.tsx:
  challenge = await fetch(`/api/daily-challenge/${id}`)
  return new ImageResponse(<카드 JSX>, { width: 1200, height: 630 })
```

## 5. 엣지케이스

- **잘못된 ID** → 랜딩 페이지 404 + "오늘의 챌린지 가기" 링크. OG 라우트도 generic fallback 이미지.
- **verdict 파라미터 없음** → 배지·승률 미표시, generic "일일 챌린지" 카드.
- **백엔드 다운 / 네트워크 실패** → 랜딩 페이지 fallback UI(에러 메시지 + 홈 링크). OG 라우트는 generic 카드.
- **`navigator.share` 미지원** → 클립보드 복사 + 토스트. Clipboard API도 미지원이면 `prompt()`로 URL 노출.
- **iOS PWA 환경의 share** → 표준 Web Share API로 동작 확인 필요.

## 6. 테스트

### 6.1 백엔드 단위

`backend/tests/api/test_daily.py`에 추가.

- `test_get_by_id_returns_challenge` — 알려진 ID에 대해 200 + 직렬화 필드 일치.
- `test_get_by_id_unknown_404` — 존재하지 않는 ID에 404.

### 6.2 프론트엔드 단위 (Vitest)

`web/tests/share-button.test.ts` (또는 컴포넌트별).

- `navigator.share` mock 호출 검증.
- mock 미지원 시 `navigator.clipboard.writeText` 폴백 호출 검증.
- 토스트 메시지 발생 확인.

### 6.3 수동 검증 체크리스트 (PR 본문에 포함)

- [ ] verdict 4가지(best/ok/weak/miss) 모두에서 공유 동작.
- [ ] iOS Safari `navigator.share` 시스템 시트 호출.
- [ ] Android Chrome `navigator.share` 시스템 시트 호출.
- [ ] 데스크탑 Chrome — 클립보드 복사 + 토스트.
- [ ] 카카오톡에 링크 붙여 og 카드 표시 확인.
- [ ] 트위터/X에 링크 붙여 og 카드 표시 확인.
- [ ] 디스코드에 링크 붙여 og 카드 표시 확인.
- [ ] 잘못된 ID 링크 → 404 fallback UI 정상.
- [ ] 다크모드에서 랜딩 페이지 토큰 준수(`design-token-guardian` 통과).
- [ ] 공유 버튼 키보드 포커스·`aria-label` 확인(`a11y-auditor` 통과).

## 7. 디자인 시스템 준수

- 색은 토큰만 사용(`text-ink`, `text-ink-mute`, `bg-paper`, `oxblood`, `moss`, `gold`).
- 라운드: 카드 `rounded-none`, 배지 `rounded-sm`, 토글성 요소 없음.
- 그림자 없음.
- 아이콘은 `lucide-react`. 공유 버튼은 `Share2` 아이콘 16px, `strokeWidth={1.5}`.
- 이모지 금지.
- 모든 한국어 문구는 i18n 통과.

## 8. 일정·범위 추정

- 백엔드 엔드포인트 + 테스트: ~30분.
- `StaticBoardSVG` 컴포넌트: ~30분.
- `ShareButton` + i18n: ~30분.
- 랜딩 페이지: ~45분.
- OG 라우트(`next/og`): ~60분(폰트·레이아웃 튜닝 포함).
- 통합·수동 QA: ~30분.

합 3.5~4시간 분량의 단일 PR.

## 9. 결정 로그

- 워들식 누적 공유보다 단일 문제 결과 공유 선택 — DB 스키마 변경 없이 즉시 출시 가능. 추후 streak 기능은 별도 스펙.
- 답수·정답 표시 안 함 — 받는 사람이 같은 도전을 받을 수 있도록.
- 카카오 SDK 직접 연동 대신 Web Share API + og:image — 카톡도 og 표준을 지원.
- 결과 위변조 서명 미적용 — 자랑용 카드 수준에서 영향 미미, 복잡도 회피.
- 클라이언트 canvas 대신 서버측 `next/og` — 메시지 앱 자동 프리뷰가 핵심 가치.

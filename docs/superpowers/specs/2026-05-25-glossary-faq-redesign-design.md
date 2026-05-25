# Glossary · FAQ UI/UX Redesign (Editorial Encyclopedia + Accordion)

- 작성일: 2026-05-25
- 상태: 설계 승인 완료, 구현 계획 대기
- 범위: `/glossary`·`/glossary/[slug]`·`/faq`·`/faq/[slug]` 4개 페이지를 사이트 Editorial Hardcover 디자인 시스템에 맞춰 재구성

## 배경

content-draft 파이프라인이 만든 글로서리·FAQ는 라이브 응답하지만 4 페이지 모두
`<article className="prose">` + `<ul>` 또는 `dangerouslySetInnerHTML`로 다듬지
않은 "테스트 페이지" 수준. 사이트의 Editorial Hardcover/Journal 디자인 시스템
(Hero·RuleDivider·토큰 컬러·serif/sans 타이포)이 갖춰져 있는데도 이 두 영역은
그 톤과 단절되어 있어 발견·읽기·전환 어느 시나리오도 받쳐주지 못한다.

## 목표 / 비목표

### 목표

세 사용자 시나리오 균형:
1. **교양/독서** — 정독·관련 항목 탐색
2. **게임 중 빠른 참조** — 검색/펼침으로 5초 안에 답
3. **SEO 랜딩** — 외부 유입의 첫 인상 + CTA로 inkbaduk 경험 전환

### 비목표 (YAGNI)

- 카테고리/태그 시스템 (현재 글로서리 3·FAQ 1, 무의미)
- 검색 결과 텍스트 하이라이팅
- 평점·코멘트·소셜 공유 버튼
- 인쇄 최적화 CSS
- 다국어 콘텐츠 자체 (UI i18n은 하되 콘텐츠는 한국어만)
- 무한 스크롤·페이지네이션 (수백 개까지 단일 페이지 OK)
- FAQ 다중 펼침
- 글로서리 카드 hover popover
- 글로서리·FAQ 콘텐츠 자체 수정 (이번 PR은 표현 layer만)

## 결정된 접근 — C (하이브리드)

검토한 3안 (Editorial Encyclopedia / Interactive Field Guide / Hybrid) 중
**Hybrid (글로서리 카드 그리드 + FAQ Accordion)** 채택.

근거:
- FAQ는 본질적으로 Q→A 짝이라 accordion이 표준 UX (한 화면 스캔 + 펼침)
- 글로서리는 사전이라 카드 그리드 + 상세가 자연 — 90개로 자라면 accordion 비현실
- 두 페이지 패턴이 다른 게 오히려 "각 자리에 맞는 도구" 신호

## 설계

### 섹션 1 — 글로서리 인덱스 `/glossary`

**구조**
1. **Hero** — `<Hero size="compact" volume="VOL. I · 용어" title="바둑 사전" subtitle="KataGo와 두며 만나는 N가지 개념" />`. N은 동적 카운트.
2. **검색 + 초성 필터** (`ContentSearchFilter` 신규)
   - shadcn `Input` 검색바, 제목/슬러그 부분 일치, 클라이언트 사이드
   - 한글 초성 chips (`전체 ㄱ ㄴ ㄷ ㄹ ㅁ ㅂ ㅅ ㅇ ㅈ ㅊ ㅋ ㅌ ㅍ ㅎ`). 슬러그의 한글 첫 글자 초성 추출
   - chip 활성 토글: 한 번 누름. 검색과 AND 조건
3. **카드 그리드** (`ContentCard` 신규, `web/components/editorial/`)
   - `<Link>` 전체 클릭 가능
   - 제목 font-serif 2xl + 로마자 슬러그 font-mono uppercase tracking-label text-ink-faint
   - `<RuleDivider weight="weak" />`
   - excerpt 1-2줄 (`line-clamp-2`)
   - `자세히 →` 푸터 (oxblood, font-mono uppercase)
   - border-ink-faint → hover:border-oxblood transition-base
   - 그리드: `grid gap-4 sm:grid-cols-2 lg:grid-cols-3`
4. **빈 상태** — `<EmptyState />` (검색·필터 결과 0)

**클라이언트 컴포넌트**: 검색·필터 상태가 있어야 하므로 `"use client"` 필요. 인덱스 page.tsx는 서버 컴포넌트로 두고 `ContentSearchFilter`만 client (props로 items 받음). 메타데이터는 서버에서.

### 섹션 2 — 글로서리 상세 `/glossary/[slug]`

**구조**
1. **Breadcrumb** — `용어 / {title}` (font-mono text-xs uppercase tracking-label text-ink-faint, "용어" 부분 `<Link href="/glossary">`)
2. **Hero compact** — volume = slug uppercase (oxblood), title = title, subtitle = excerpt
3. **본문 article** — `dangerouslySetInnerHTML` 유지하되 wrapper에 `className="editorial-prose"` 적용. 토큰 매핑 (h2 font-serif, link oxblood, blockquote border-l-oxblood, code font-mono bg-paper-deep)
4. **푸터 네비**
   - 알파벳 순 prev/next 항목 (slugs sort, 인접): `← 이전: 빅`, `다음: 패 →`
   - `[대국 시작 →]` CTA Button variant default oxblood → `/game/new`
   - 가운데 `<RuleDivider weight="strong" />`로 본문과 분리

**서버 컴포넌트**: 정적 콘텐츠 + 마크다운 SSR. client 코드 없음. SEO·canonical 유지.

### 섹션 3 — FAQ 인덱스 `/faq` (Accordion)

**선행 의존**: shadcn `accordion` 컴포넌트 설치 (`npx shadcn@latest add accordion`). 토큰 재스타일링 필요.

**구조**
1. **Hero compact** — volume = "자주 묻는 질문", title = "FAQ", subtitle = "N가지 답변. 못 찾았으면 지원 페이지로."
2. **단일 펼침 Accordion** (`type="single"`, `collapsible`)
   - 각 item value = slug
   - 트리거: 질문 (font-serif text-lg) + chevron (lucide `ChevronDown`, rotate-180 on open)
   - 본문: editorial-prose 인라인 마크다운
   - 사이에 RuleDivider weak
3. **URL hash 자동 펼침**: 마운트 시 `window.location.hash`를 읽어 매칭 slug 펼치고 scroll
4. **푸터 CTA**: `질문 못 찾으셨나요?` + `<Link href="/support">지원 페이지 →</Link>`

**클라이언트 컴포넌트**: accordion 상태 + hash. 인덱스 page.tsx는 서버에서 데이터 fetch + `ContentAccordion` (신규 client wrapper)에 props로 전달.

### 섹션 4 — FAQ 상세 `/faq/[slug]`

글로서리 상세와 동일 구조 (Breadcrumb + Hero compact + article + 푸터 네비).
- Breadcrumb: `FAQ / {title}`
- Hero: volume = "FAQ"
- 푸터: prev/next + `대국 시작` CTA
- canonical 그대로 자기 페이지 유지 (인덱스 accordion이 모든 답을 노출하지만 SEO/공유 위해 상세 페이지 유지)

### 섹션 5 — 공통 인프라

**`lib/content.ts` 보강**
- `ContentItem`에 `excerpt: string` 필드 추가
- 추출 로직: frontmatter `excerpt`가 있으면 사용, 없으면 본문 마크다운 첫 문장 (마침표·물음표·느낌표까지) 또는 첫 100자
- 한국어 문장 종결 처리 정확히

**신규 컴포넌트** (`web/components/editorial/`)
- `ContentCard.tsx` — 글로서리 카드 (재사용 가능 구조)
- `ContentSearchFilter.tsx` — 검색 input + 초성 chips + 필터 결과 자식 렌더 (render props 패턴)
- `ContentAccordion.tsx` — FAQ accordion 묶음
- 한국어 초성 추출 유틸 `lib/hangul.ts` (작은 헬퍼; 유니코드 코드포인트 산술)

**EditorialProse 스타일**
- `web/app/globals.css`에 `.editorial-prose` 클래스 추가
- 토큰 매핑:
  - `h2/h3`: font-serif font-semibold, h2 text-2xl mt-8, h3 text-xl mt-6
  - `p`: font-sans text-base leading-relaxed text-ink mt-4
  - `a`: text-oxblood underline-offset-4 hover:underline
  - `strong`: font-semibold text-ink
  - `blockquote`: border-l-2 border-oxblood pl-4 italic text-ink-mute
  - `code`: font-mono text-sm bg-paper-deep px-1 rounded-sm
  - `ul/ol`: pl-6 mt-4 marker:text-ink-mute
  - 첫 `<p>` lead 처리: `:first-child` font-serif text-lg leading-snug (선택사항)

**i18n 키 추가** (ko/en 동시, inline 포맷 유지)
- `glossary.heroVolume` "VOL. I · 용어" / "VOL. I · Glossary"
- `glossary.heroTitle` "바둑 사전" / "Baduk Dictionary"
- `glossary.heroSubtitle` "KataGo와 두며 만나는 {count}가지 개념" / "{count} concepts you meet playing KataGo"
- `glossary.searchPlaceholder` "용어 검색…" / "Search terms…"
- `glossary.filterAll` "전체" / "All"
- `glossary.cardMore` "자세히 →" / "Read more →"
- `glossary.prevEntry` "이전" / "Previous"
- `glossary.nextEntry` "다음" / "Next"
- `glossary.startGameCta` "대국 시작 →" / "Start a game →"
- `glossary.empty` "검색 결과 없음" / "No matches"
- `faq.heroTitle` "FAQ" / "FAQ"
- `faq.heroSubtitle` "{count}가지 답변" / "{count} answers"
- `faq.notFoundCta` "질문 못 찾으셨나요? 지원 페이지 →" / "Didn't find your question? Support →"
- `breadcrumb.glossary` "용어" / "Glossary"
- `breadcrumb.faq` "FAQ" / "FAQ"

총 15 키. **FAQ 상세 페이지의 prev/next·CTA는 `glossary.*` 키 재사용** (의미적으로 동일 — "이전·다음·대국 시작"). 별도 `faq.*` 변형 키 만들지 않음.

## 컴포넌트 / 파일 매트릭스

| 파일 | 종류 | 책임 |
|---|---|---|
| `web/app/glossary/page.tsx` | 수정 (server) | Hero + 데이터 → `ContentSearchFilter` |
| `web/app/glossary/[slug]/page.tsx` | 수정 (server) | Breadcrumb + Hero + article + prev/next |
| `web/app/faq/page.tsx` | 수정 (server) | Hero + 데이터 → `ContentAccordion` |
| `web/app/faq/[slug]/page.tsx` | 수정 (server) | Breadcrumb + Hero + article + prev/next |
| `web/components/editorial/ContentCard.tsx` | 신규 | 글로서리 카드 한 개 |
| `web/components/editorial/ContentSearchFilter.tsx` | 신규 client | 검색·초성 + 카드 그리드 렌더 |
| `web/components/editorial/ContentAccordion.tsx` | 신규 client | FAQ accordion 묶음 + hash 자동 펼침 |
| `web/components/ui/accordion.tsx` | shadcn add | Radix accordion 래퍼 |
| `web/lib/content.ts` | 수정 | `excerpt` 필드 추가 |
| `web/lib/hangul.ts` | 신규 | 한글 초성 추출 유틸 |
| `web/app/globals.css` | 수정 | `.editorial-prose` 클래스 |
| `web/lib/i18n/ko.json` · `en.json` | 수정 | 15키 인라인 추가 |

## 데이터 흐름

```
content/glossary/*.md ──┐
                        ├── getContent / getContentSlugs (server)
content/faq/*.md ───────┘                │
                                          ├── excerpt 추출
                                          ▼
                              Server Component (page.tsx)
                                          │
                                          ├── glossary: items → ContentSearchFilter (client)
                                          │       └── ContentCard × N (서버 렌더 가능하지만 단순화 위해 client 안에서)
                                          │
                                          └── faq: items → ContentAccordion (client)
                                                  └── shadcn AccordionItem × N
```

마크다운 → html 변환은 server에서만 (`marked`). client에는 이미 변환된 html 문자열만 전달.

## 테스트

- **단위**: `lib/content.ts::extractExcerpt` 헬퍼 — 한국어 마침표, frontmatter excerpt 우선, 빈 본문 케이스. Vitest 추가.
- **단위**: `lib/hangul.ts::leadConsonant` — `축→ㅊ`, `빅→ㅂ`, `dan-gup→null` (영문 시작), 빈 문자열 → null.
- **렌더링**: vitest + testing-library로 `ContentCard`, `ContentSearchFilter`(필터링 동작), `ContentAccordion`(hash 펼침). 기존 vitest 설정 활용.
- **시각**: 별도 visual-qa 에이전트로 라이브 light/dark 4페이지 캡처 (PR 후).

## 위험 / 미해결

1. **shadcn accordion 토큰 재스타일링** — shadcn 기본은 rounded·shadow가 있다. Editorial 톤(rounded-none, no shadow, RuleDivider)으로 변형 필요. 추가 css 적용으로 해결.
2. **본문 마크다운의 lead 처리** — 첫 `<p>`만 lead 스타일링은 `:first-child`로 단순 처리. 본문 구조가 frontmatter 다음 바로 `<p>`가 아닌 경우 (예: `<ul>` 먼저) lead 스킵.
3. **한국어 첫 문장 추출** — `.`·`?`·`!` 외에 `…`·`다.` 등도 종결 후보. 단순화: 처음 100자 또는 첫 `[.!?]` 중 짧은 쪽.
4. **prev/next 알파벳 순 인접** — slugs sort 후 인덱스 위치 ±1. 첫·끝 항목 wrap 안 함 (단일 방향만 표시).
5. **카드 내부에 `<Link>` 중첩 위험** — "자세히 →" 텍스트는 시각적 강조만, 카드 전체가 `<Link>`. 중첩 link 금지.
6. **검색·초성 필터의 SSR 미리보기** — 첫 페인트에는 모든 항목 보임 (`useState` 초기값 "전체"). hydration 후에도 동일 결과라 깜박임 없음.

## 단계 분해 (writing-plans에서 상세)

1. `lib/content.ts` `excerpt` 추출 + 단위 테스트
2. `lib/hangul.ts` 초성 헬퍼 + 단위 테스트
3. shadcn accordion 추가 + Editorial 토큰 재스타일
4. `web/app/globals.css` `.editorial-prose` 클래스
5. i18n ko/en 15키 인라인 추가
6. `ContentCard` 컴포넌트 + 테스트
7. `ContentSearchFilter` 컴포넌트 + 테스트
8. `ContentAccordion` 컴포넌트 + 테스트
9. `/glossary` 인덱스 page.tsx 재구성
10. `/glossary/[slug]` 상세 page.tsx 재구성 + prev/next
11. `/faq` 인덱스 page.tsx 재구성
12. `/faq/[slug]` 상세 page.tsx 재구성 + prev/next
13. `type-check`·`lint`·`vitest` 통과 + 시각 회귀 (라이브 머지 후)

총 13 task, 단일 PR로 묶음.

## 자율성 등급

- 모든 코드/컴포넌트/테스트 = 🟢 자율 (worktree)
- main 머지 + 라이브 build + web kickstart = 🟡 사람 승인 (지금 세션의 기존 패턴)

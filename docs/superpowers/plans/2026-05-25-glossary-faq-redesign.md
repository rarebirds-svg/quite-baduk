# Glossary · FAQ UI/UX Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 글로서리(인덱스 카드 그리드 + 검색·초성 필터 + 상세 article)와 FAQ(인덱스 accordion + 상세 article) 4개 페이지를 Editorial Hardcover 디자인 시스템에 맞춰 재구성한다.

**Architecture:** server 컴포넌트로 페이지 데이터 fetch → client wrapper(`ContentSearchFilter`·`ContentAccordion`)에 props 전달, 새 editorial 프리미티브(`ContentCard`) + 신규 `lib/content.excerpt` 추출 + `lib/hangul.leadConsonant` 헬퍼 + 전역 `.editorial-prose` 마크다운 토큰 매핑. shadcn `accordion` (Radix 기반)을 신규 ui 컴포넌트로 추가하되 Editorial 토큰으로 재스타일.

**Tech Stack:** Next.js 14 App Router, TypeScript strict, Tailwind 토큰만, shadcn(Radix), `marked`/`gray-matter` (server-only), vitest + @testing-library/react (client 컴포넌트), lucide-react 아이콘.

**Spec:** [`docs/superpowers/specs/2026-05-25-glossary-faq-redesign-design.md`](../specs/2026-05-25-glossary-faq-redesign-design.md)

**중요 정정:** spec에서 `<RuleDivider weight="weak" />`로 적힌 부분이 있는데, 실제 prop은 `"faint" | "strong"`이다. 본 plan 전체에서 **`weight="faint"`** 로 통일한다.

**자율성 게이트:** 모든 코드/테스트 = 🟢 자율. main 머지 + 라이브 build + web kickstart = 🟡 사람 승인 (PR 단계).

---

## Task 1: `lib/content.ts` `excerpt` 추출 + 단위 테스트

**Files:**
- Modify: `web/lib/content.ts`
- Create: `web/tests/content.excerpt.test.ts`

- [ ] **Step 1: 실패 테스트 작성**

Create `web/tests/content.excerpt.test.ts`:

```ts
// excerpt 추출 헬퍼 단위 테스트.
import { describe, it, expect } from "vitest";
import { extractExcerpt } from "../lib/content";

describe("extractExcerpt", () => {
  it("returns override when frontmatter excerpt exists", () => {
    expect(extractExcerpt("Body text.", "Manual excerpt.")).toBe("Manual excerpt.");
  });

  it("returns first sentence terminated by .", () => {
    expect(extractExcerpt("축은 기본 기술이다. 두 번째 문장.")).toBe("축은 기본 기술이다.");
  });

  it("returns first sentence terminated by ?", () => {
    expect(extractExcerpt("질문인가요? 답변 문장.")).toBe("질문인가요?");
  });

  it("returns first sentence terminated by !", () => {
    expect(extractExcerpt("강조! 다음.")).toBe("강조!");
  });

  it("strips markdown headers and list markers from leading content", () => {
    expect(extractExcerpt("# 제목\n\n첫 문단 시작. 다음.")).toBe("첫 문단 시작.");
  });

  it("strips bold and inline code markers", () => {
    expect(extractExcerpt("이건 **굵은** `코드` 문장.")).toBe("이건 굵은 코드 문장.");
  });

  it("falls back to first paragraph then truncates over 100 chars", () => {
    const long = "가".repeat(150);
    const out = extractExcerpt(long);
    expect(out.endsWith("…")).toBe(true);
    expect([...out].length).toBeLessThanOrEqual(101);
  });

  it("returns empty string for empty content with no override", () => {
    expect(extractExcerpt("")).toBe("");
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run from `web/`:
```
npx vitest run tests/content.excerpt.test.ts
```
Expected: FAIL (`extractExcerpt is not a function`).

- [ ] **Step 3: `extractExcerpt` 구현 + `getContent` 통합**

Modify `web/lib/content.ts`:

```ts
// web/content/<kind>/<slug>.md 마크다운 콘텐츠 reader — frontmatter 파싱 + html 렌더.
import fs from "node:fs";
import path from "node:path";

import matter from "gray-matter";
import { marked } from "marked";

const CONTENT_ROOT = path.join(process.cwd(), "content");

export type ContentKind = "glossary" | "faq";

export interface ContentItem {
  slug: string;
  kind: ContentKind;
  title: string;
  created_at?: string;
  excerpt: string;
  html: string;
}

function contentDir(kind: ContentKind): string {
  return path.join(CONTENT_ROOT, kind);
}

export function getContentSlugs(kind: ContentKind): string[] {
  const dir = contentDir(kind);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".md"))
    .map((f) => f.replace(/\.md$/, ""))
    .sort();
}

export function extractExcerpt(content: string, override?: string): string {
  if (override && override.trim()) return override.trim();
  if (!content) return "";
  const plain = content
    .replace(/^#+\s+.*$/gm, "")
    .replace(/^\s*[-*]\s+/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .trim();
  const firstPara = plain.split(/\n\n+/)[0]?.trim() ?? "";
  const sentenceMatch = firstPara.match(/^([\s\S]*?[.!?])(\s|$)/);
  const candidate = sentenceMatch ? sentenceMatch[1].trim() : firstPara;
  if ([...candidate].length > 100) {
    return [...candidate].slice(0, 100).join("") + "…";
  }
  return candidate;
}

export function getContent(kind: ContentKind, slug: string): ContentItem | null {
  const file = path.join(contentDir(kind), `${slug}.md`);
  if (!fs.existsSync(file)) return null;
  const raw = fs.readFileSync(file, "utf-8");
  const { data, content } = matter(raw);
  if (data.kind !== kind) return null;
  if (data.slug !== slug) return null;
  const html = marked.parse(content, { async: false }) as string;
  const excerpt = extractExcerpt(
    content,
    typeof data.excerpt === "string" ? data.excerpt : undefined,
  );
  return {
    slug,
    kind,
    title: String(data.title ?? slug),
    created_at: data.created_at ? String(data.created_at) : undefined,
    excerpt,
    html,
  };
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run from `web/`:
```
npx vitest run tests/content.excerpt.test.ts
```
Expected: 8 passed.

- [ ] **Step 5: 기존 content.test.ts (있다면) 회귀 확인**

Run from `web/`:
```
npx vitest run tests/content.test.ts
```
Expected: 모두 PASS. 새 `excerpt` 필드가 기존 인터페이스 사용에 영향 없는지 확인.

- [ ] **Step 6: Commit**

```bash
git add web/lib/content.ts web/tests/content.excerpt.test.ts
git commit -m "feat(content): extractExcerpt + ContentItem.excerpt 필드 추가"
```

---

## Task 2: `lib/hangul.ts` 초성 추출 + 단위 테스트

**Files:**
- Create: `web/lib/hangul.ts`
- Create: `web/tests/hangul.test.ts`

- [ ] **Step 1: 실패 테스트 작성**

Create `web/tests/hangul.test.ts`:

```ts
// 한글 초성 추출 유틸 단위 테스트.
import { describe, it, expect } from "vitest";
import { leadConsonant, CHOSEONG_BASE } from "../lib/hangul";

describe("leadConsonant", () => {
  it("returns ㅂ for 빅", () => expect(leadConsonant("빅")).toBe("ㅂ"));
  it("returns ㅊ for 축", () => expect(leadConsonant("축")).toBe("ㅊ"));
  it("returns ㄷ for 단·급", () => expect(leadConsonant("단·급")).toBe("ㄷ"));
  it("maps tense ㄲ → ㄱ", () => expect(leadConsonant("까")).toBe("ㄱ"));
  it("returns null for ascii start", () => expect(leadConsonant("dan-gup")).toBe(null));
  it("returns null for empty string", () => expect(leadConsonant("")).toBe(null));
  it("returns null for emoji or symbol start", () => expect(leadConsonant("★축")).toBe(null));
});

describe("CHOSEONG_BASE", () => {
  it("has 14 base consonants in order", () => {
    expect(CHOSEONG_BASE).toEqual(["ㄱ","ㄴ","ㄷ","ㄹ","ㅁ","ㅂ","ㅅ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]);
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run from `web/`:
```
npx vitest run tests/hangul.test.ts
```
Expected: FAIL (module not found).

- [ ] **Step 3: `lib/hangul.ts` 구현**

Create `web/lib/hangul.ts`:

```ts
// 한글 초성 추출 — 사전/글로서리 필터 chip용.
const CHOSEONG_ALL = [
  "ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ",
] as const;

const TENSE_TO_BASE: Record<string, string> = {
  "ㄲ": "ㄱ",
  "ㄸ": "ㄷ",
  "ㅃ": "ㅂ",
  "ㅆ": "ㅅ",
  "ㅉ": "ㅈ",
};

export const CHOSEONG_BASE = ["ㄱ","ㄴ","ㄷ","ㄹ","ㅁ","ㅂ","ㅅ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"] as const;

export function leadConsonant(text: string): string | null {
  if (!text) return null;
  const code = text.charCodeAt(0);
  if (code < 0xAC00 || code > 0xD7A3) return null;
  const index = Math.floor((code - 0xAC00) / 588);
  const cho = CHOSEONG_ALL[index];
  return TENSE_TO_BASE[cho] ?? cho;
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run from `web/`:
```
npx vitest run tests/hangul.test.ts
```
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add web/lib/hangul.ts web/tests/hangul.test.ts
git commit -m "feat(lib): 한글 초성 추출 유틸 (leadConsonant + CHOSEONG_BASE)"
```

---

## Task 3: shadcn accordion 컴포넌트 + Editorial 토큰 재스타일

**Files:**
- Create: `web/components/ui/accordion.tsx`
- Modify: `web/package.json` (의존성 추가 시)

- [ ] **Step 1: `@radix-ui/react-accordion` 의존성 확인 + 설치**

Check from `web/`:
```
grep -E '"@radix-ui/react-accordion"' package.json || echo "missing"
```

If missing, install:
```
npm install @radix-ui/react-accordion
```

- [ ] **Step 2: Editorial 토큰을 입힌 accordion 컴포넌트 작성**

Create `web/components/ui/accordion.tsx`:

```tsx
"use client";
// Radix accordion 래퍼 — Editorial 토큰(rounded-none, no shadow, RuleDivider hairline)으로 재스타일.
import * as React from "react";
import * as AccordionPrimitive from "@radix-ui/react-accordion";
import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/cn";

const Accordion = AccordionPrimitive.Root;

const AccordionItem = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Item>
>(({ className, ...props }, ref) => (
  <AccordionPrimitive.Item
    ref={ref}
    className={cn("border-t border-ink-faint last:border-b", className)}
    {...props}
  />
));
AccordionItem.displayName = "AccordionItem";

const AccordionTrigger = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <AccordionPrimitive.Header className="flex">
    <AccordionPrimitive.Trigger
      ref={ref}
      className={cn(
        "flex flex-1 items-center justify-between gap-4 py-5 text-left font-serif text-lg font-semibold text-ink transition-base [&[data-state=open]>svg]:rotate-180 hover:text-oxblood",
        className,
      )}
      {...props}
    >
      {children}
      <ChevronDown
        size={18}
        strokeWidth={1.5}
        className="shrink-0 text-ink-mute transition-base duration-300"
      />
    </AccordionPrimitive.Trigger>
  </AccordionPrimitive.Header>
));
AccordionTrigger.displayName = "AccordionTrigger";

const AccordionContent = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <AccordionPrimitive.Content
    ref={ref}
    className="overflow-hidden data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down"
    {...props}
  >
    <div className={cn("pb-6 pt-0", className)}>{children}</div>
  </AccordionPrimitive.Content>
));
AccordionContent.displayName = "AccordionContent";

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent };
```

- [ ] **Step 3: tailwind 애니메이션 키프레임 확인 (기존 사용 또는 추가)**

Check from `web/`:
```
grep -E "(accordion-up|accordion-down)" tailwind.config.* app/globals.css
```

If missing, add to `web/app/globals.css` (안에 기존 `@layer utilities` 또는 keyframes 섹션 어디든):

```css
@layer utilities {
  @keyframes accordion-down {
    from { height: 0 }
    to { height: var(--radix-accordion-content-height) }
  }
  @keyframes accordion-up {
    from { height: var(--radix-accordion-content-height) }
    to { height: 0 }
  }
  .animate-accordion-down { animation: accordion-down 200ms ease-out }
  .animate-accordion-up { animation: accordion-up 200ms ease-out }
}
```

- [ ] **Step 4: 타입 검증**

Run from `web/`:
```
npm run type-check
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add web/components/ui/accordion.tsx web/package.json web/package-lock.json web/app/globals.css
git commit -m "feat(ui): Editorial 토큰 입힌 Radix Accordion 컴포넌트"
```

---

## Task 4: `.editorial-prose` 클래스 (globals.css)

**Files:**
- Modify: `web/app/globals.css`

- [ ] **Step 1: globals.css에 `.editorial-prose` 추가**

Modify `web/app/globals.css` — `@layer utilities` 끝 또는 별도 layer:

```css
@layer components {
  /* 마크다운 본문 (글로서리·FAQ)에 사이트 토큰을 적용. prose 대체. */
  .editorial-prose {
    @apply font-sans text-base leading-relaxed text-ink;
  }
  .editorial-prose > * + * { @apply mt-4; }
  .editorial-prose h2 {
    @apply font-serif text-2xl font-semibold text-ink mt-10 mb-2;
  }
  .editorial-prose h3 {
    @apply font-serif text-xl font-semibold text-ink mt-8 mb-2;
  }
  .editorial-prose p {
    @apply font-sans text-base leading-relaxed text-ink;
  }
  .editorial-prose a {
    @apply text-oxblood underline underline-offset-4 hover:opacity-80 transition-base;
  }
  .editorial-prose strong {
    @apply font-semibold text-ink;
  }
  .editorial-prose em {
    @apply italic;
  }
  .editorial-prose blockquote {
    @apply border-l-2 border-oxblood pl-4 italic text-ink-mute;
  }
  .editorial-prose code {
    @apply font-mono text-sm bg-paper-deep px-1.5 py-0.5 rounded-sm text-ink;
  }
  .editorial-prose pre {
    @apply font-mono text-sm bg-paper-deep p-4 overflow-x-auto rounded-sm;
  }
  .editorial-prose ul {
    @apply list-disc pl-6 marker:text-ink-mute;
  }
  .editorial-prose ol {
    @apply list-decimal pl-6 marker:text-ink-mute;
  }
  .editorial-prose li {
    @apply mt-1;
  }
  .editorial-prose hr {
    @apply border-t border-ink-faint my-8;
  }
}
```

- [ ] **Step 2: build 검증 (CSS 컴파일)**

Run from `web/`:
```
npm run build 2>&1 | tail -5
```
Expected: build 성공.

- [ ] **Step 3: Commit**

```bash
git add web/app/globals.css
git commit -m "feat(css): .editorial-prose 클래스 — 마크다운 본문 토큰 매핑"
```

---

## Task 5: i18n ko/en 15키 인라인 추가

**Files:**
- Modify: `web/lib/i18n/ko.json`
- Modify: `web/lib/i18n/en.json`

- [ ] **Step 1: 두 파일을 동시 편집 (인라인 포맷 유지)**

먼저 현재 `glossary`·`faq`·`breadcrumb` 섹션이 있는지 확인:
```
grep -E '"(glossary|faq|breadcrumb)"' web/lib/i18n/ko.json | head -3
```

존재하지 않을 가능성 큼 — 새 섹션 추가.

`ko.json` 끝 부분의 닫는 `}` 직전에 (마지막 항목 뒤 쉼표 처리 주의) 인라인 한 줄씩 추가:

```json
  "glossary": { "heroVolume": "VOL. I · 용어", "heroTitle": "바둑 사전", "heroSubtitle": "KataGo와 두며 만나는 {count}가지 개념", "searchPlaceholder": "용어 검색…", "filterAll": "전체", "cardMore": "자세히 →", "prevEntry": "이전", "nextEntry": "다음", "startGameCta": "대국 시작 →", "empty": "검색 결과 없음" },
  "faq": { "heroTitle": "FAQ", "heroSubtitle": "{count}가지 답변", "notFoundCta": "질문 못 찾으셨나요? 지원 페이지 →" },
  "breadcrumb": { "glossary": "용어", "faq": "FAQ" }
```

`en.json`도 같은 구조로:

```json
  "glossary": { "heroVolume": "VOL. I · Glossary", "heroTitle": "Baduk Dictionary", "heroSubtitle": "{count} concepts you meet playing KataGo", "searchPlaceholder": "Search terms…", "filterAll": "All", "cardMore": "Read more →", "prevEntry": "Previous", "nextEntry": "Next", "startGameCta": "Start a game →", "empty": "No matches" },
  "faq": { "heroTitle": "FAQ", "heroSubtitle": "{count} answers", "notFoundCta": "Didn't find your question? Support →" },
  "breadcrumb": { "glossary": "Glossary", "faq": "FAQ" }
```

**중요**: Edit 도구로 직접 인라인 라인 삽입 (python json.dump 사용 금지 — reformat churn 방지).

- [ ] **Step 2: JSON 유효성 + 줄 수 확인**

Run from `web/`:
```
python3 -c "import json; json.load(open('lib/i18n/ko.json')); json.load(open('lib/i18n/en.json')); print('OK')"
wc -l lib/i18n/ko.json lib/i18n/en.json
```
Expected: `OK` + 줄 수가 기존 +3 정도 (3개 inline 객체 추가).

- [ ] **Step 3: type-check**

Run from `web/`:
```
npm run type-check
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "feat(i18n): 글로서리·FAQ·breadcrumb 키 15개 인라인 추가 (ko/en)"
```

---

## Task 6: `ContentCard` 컴포넌트 + 테스트

**Files:**
- Create: `web/components/editorial/ContentCard.tsx`
- Create: `web/tests/editorial/ContentCard.test.tsx`

- [ ] **Step 1: 실패 테스트 작성**

Create `web/tests/editorial/ContentCard.test.tsx`:

```tsx
// ContentCard 렌더 테스트.
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ContentCard } from "../../components/editorial/ContentCard";

describe("ContentCard", () => {
  const item = {
    href: "/glossary/chuk",
    title: "축",
    slug: "chuk",
    excerpt: "직선으로 추격하면서 활로를 줄여 잡는 기본 기술.",
    ctaLabel: "자세히 →",
  };

  it("renders title, slug, excerpt, and cta", () => {
    render(<ContentCard {...item} />);
    expect(screen.getByText("축")).toBeInTheDocument();
    expect(screen.getByText("CHUK")).toBeInTheDocument(); // uppercased slug
    expect(screen.getByText(item.excerpt)).toBeInTheDocument();
    expect(screen.getByText(item.ctaLabel)).toBeInTheDocument();
  });

  it("wraps the whole card in a Link to href", () => {
    render(<ContentCard {...item} />);
    const link = screen.getByRole("link", { name: /축/ });
    expect(link).toHaveAttribute("href", "/glossary/chuk");
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run from `web/`:
```
npx vitest run tests/editorial/ContentCard.test.tsx
```
Expected: FAIL.

- [ ] **Step 3: ContentCard 컴포넌트 작성**

Create `web/components/editorial/ContentCard.tsx`:

```tsx
// 글로서리·콘텐츠용 카드 — title + 슬러그 + 짧은 excerpt + CTA, 전체가 Link.
import * as React from "react";
import Link from "next/link";

import { cn } from "@/lib/cn";
import { RuleDivider } from "./RuleDivider";

export interface ContentCardProps {
  href: string;
  title: string;
  slug: string;
  excerpt: string;
  ctaLabel: string;
  className?: string;
}

export function ContentCard({ href, title, slug, excerpt, ctaLabel, className }: ContentCardProps) {
  return (
    <Link
      href={href}
      className={cn(
        "group flex flex-col gap-3 border border-ink-faint bg-paper p-5 transition-base hover:border-oxblood",
        className,
      )}
    >
      <div className="flex flex-col gap-1">
        <h3 className="font-serif text-2xl font-semibold leading-tight text-ink">{title}</h3>
        <span className="font-mono text-[11px] font-semibold uppercase tracking-label text-ink-faint">
          {slug.toUpperCase()}
        </span>
      </div>
      <RuleDivider weight="faint" />
      <p className="font-sans text-sm leading-relaxed text-ink-mute line-clamp-2">{excerpt}</p>
      <span className="mt-auto font-mono text-xs font-semibold uppercase tracking-label text-oxblood transition-base group-hover:opacity-80">
        {ctaLabel}
      </span>
    </Link>
  );
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run from `web/`:
```
npx vitest run tests/editorial/ContentCard.test.tsx
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add web/components/editorial/ContentCard.tsx web/tests/editorial/ContentCard.test.tsx
git commit -m "feat(editorial): ContentCard 컴포넌트 — 사전형 카드 (title·slug·excerpt·CTA)"
```

---

## Task 7: `ContentSearchFilter` 컴포넌트 + 테스트

**Files:**
- Create: `web/components/editorial/ContentSearchFilter.tsx`
- Create: `web/tests/editorial/ContentSearchFilter.test.tsx`

- [ ] **Step 1: 실패 테스트 작성**

Create `web/tests/editorial/ContentSearchFilter.test.tsx`:

```tsx
// 검색·초성 필터 동작 테스트.
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ContentSearchFilter } from "../../components/editorial/ContentSearchFilter";

const ITEMS = [
  { slug: "bik", title: "빅", excerpt: "양쪽 돌이 살아 있는 상태." },
  { slug: "chuk", title: "축", excerpt: "직선으로 추격해 활로를 줄이는 기본 기술." },
  { slug: "dan-gup", title: "단·급", excerpt: "한국 바둑 실력 단위." },
];

describe("ContentSearchFilter", () => {
  it("renders all items by default", () => {
    render(
      <ContentSearchFilter
        items={ITEMS}
        searchPlaceholder="검색"
        filterAllLabel="전체"
        emptyLabel="없음"
        renderItem={(it) => <div key={it.slug}>{it.title}</div>}
      />,
    );
    expect(screen.getByText("빅")).toBeInTheDocument();
    expect(screen.getByText("축")).toBeInTheDocument();
    expect(screen.getByText("단·급")).toBeInTheDocument();
  });

  it("filters by search text (title)", () => {
    render(
      <ContentSearchFilter
        items={ITEMS}
        searchPlaceholder="검색"
        filterAllLabel="전체"
        emptyLabel="없음"
        renderItem={(it) => <div key={it.slug}>{it.title}</div>}
      />,
    );
    fireEvent.change(screen.getByPlaceholderText("검색"), { target: { value: "축" } });
    expect(screen.getByText("축")).toBeInTheDocument();
    expect(screen.queryByText("빅")).not.toBeInTheDocument();
  });

  it("filters by lead consonant chip", () => {
    render(
      <ContentSearchFilter
        items={ITEMS}
        searchPlaceholder="검색"
        filterAllLabel="전체"
        emptyLabel="없음"
        renderItem={(it) => <div key={it.slug}>{it.title}</div>}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "ㅊ" }));
    expect(screen.getByText("축")).toBeInTheDocument();
    expect(screen.queryByText("빅")).not.toBeInTheDocument();
  });

  it("shows emptyLabel when no items match", () => {
    render(
      <ContentSearchFilter
        items={ITEMS}
        searchPlaceholder="검색"
        filterAllLabel="전체"
        emptyLabel="없음"
        renderItem={(it) => <div key={it.slug}>{it.title}</div>}
      />,
    );
    fireEvent.change(screen.getByPlaceholderText("검색"), { target: { value: "zzz" } });
    expect(screen.getByText("없음")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run from `web/`:
```
npx vitest run tests/editorial/ContentSearchFilter.test.tsx
```
Expected: FAIL.

- [ ] **Step 3: 컴포넌트 작성**

Create `web/components/editorial/ContentSearchFilter.tsx`:

```tsx
"use client";
// 검색 + 한글 초성 chip 필터. 자식 렌더는 props.renderItem이 담당 (재사용성).
import * as React from "react";

import { CHOSEONG_BASE, leadConsonant } from "@/lib/hangul";
import { cn } from "@/lib/cn";

export interface FilterableItem {
  slug: string;
  title: string;
  excerpt: string;
}

export interface ContentSearchFilterProps<T extends FilterableItem> {
  items: T[];
  searchPlaceholder: string;
  filterAllLabel: string;
  emptyLabel: string;
  renderItem: (item: T) => React.ReactNode;
}

const ALL_KEY = "__ALL__";

export function ContentSearchFilter<T extends FilterableItem>({
  items,
  searchPlaceholder,
  filterAllLabel,
  emptyLabel,
  renderItem,
}: ContentSearchFilterProps<T>) {
  const [query, setQuery] = React.useState("");
  const [chip, setChip] = React.useState<string>(ALL_KEY);

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((it) => {
      if (chip !== ALL_KEY) {
        if (leadConsonant(it.title) !== chip) return false;
      }
      if (!q) return true;
      return (
        it.title.toLowerCase().includes(q) || it.slug.toLowerCase().includes(q)
      );
    });
  }, [items, query, chip]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={searchPlaceholder}
          className="h-10 w-full max-w-sm border border-ink-faint bg-paper px-3 font-sans text-sm text-ink placeholder:text-ink-faint focus:border-oxblood focus:outline-none"
        />
        <div className="flex flex-wrap gap-1">
          <ChipButton
            active={chip === ALL_KEY}
            onClick={() => setChip(ALL_KEY)}
            label={filterAllLabel}
          />
          {CHOSEONG_BASE.map((c) => (
            <ChipButton
              key={c}
              active={chip === c}
              onClick={() => setChip(c)}
              label={c}
            />
          ))}
        </div>
      </div>
      {filtered.length === 0 ? (
        <div className="border border-ink-faint bg-paper-deep px-6 py-12 text-center font-sans text-sm text-ink-mute">
          {emptyLabel}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((it) => renderItem(it))}
        </div>
      )}
    </div>
  );
}

function ChipButton({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "min-w-[2rem] border px-2 py-1 font-mono text-xs font-semibold uppercase tracking-label transition-base",
        active
          ? "border-oxblood bg-oxblood text-paper"
          : "border-ink-faint bg-paper text-ink-mute hover:border-ink",
      )}
    >
      {label}
    </button>
  );
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run from `web/`:
```
npx vitest run tests/editorial/ContentSearchFilter.test.tsx
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add web/components/editorial/ContentSearchFilter.tsx web/tests/editorial/ContentSearchFilter.test.tsx
git commit -m "feat(editorial): ContentSearchFilter — 검색·초성 chip + 결과 그리드"
```

---

## Task 8: `ContentAccordion` 컴포넌트 + 테스트

**Files:**
- Create: `web/components/editorial/ContentAccordion.tsx`
- Create: `web/tests/editorial/ContentAccordion.test.tsx`

- [ ] **Step 1: 실패 테스트 작성**

Create `web/tests/editorial/ContentAccordion.test.tsx`:

```tsx
// FAQ accordion 동작 테스트.
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ContentAccordion } from "../../components/editorial/ContentAccordion";

const ITEMS = [
  { slug: "q1", title: "첫 질문?", html: "<p>첫 답변.</p>" },
  { slug: "q2", title: "두 번째 질문?", html: "<p>두 번째 답변.</p>" },
];

describe("ContentAccordion", () => {
  it("renders all question triggers", () => {
    render(<ContentAccordion items={ITEMS} />);
    expect(screen.getByText("첫 질문?")).toBeInTheDocument();
    expect(screen.getByText("두 번째 질문?")).toBeInTheDocument();
  });

  it("uses slug as accordion item value", () => {
    const { container } = render(<ContentAccordion items={ITEMS} />);
    expect(container.querySelector('[data-radix-collection-item]')).toBeTruthy();
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run from `web/`:
```
npx vitest run tests/editorial/ContentAccordion.test.tsx
```
Expected: FAIL.

- [ ] **Step 3: 컴포넌트 작성**

Create `web/components/editorial/ContentAccordion.tsx`:

```tsx
"use client";
// FAQ 단일 펼침 accordion — URL hash로 마운트 시 자동 펼침 + scroll.
import * as React from "react";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export interface AccordionContentItem {
  slug: string;
  title: string;
  html: string;
}

export interface ContentAccordionProps {
  items: AccordionContentItem[];
}

export function ContentAccordion({ items }: ContentAccordionProps) {
  const [openSlug, setOpenSlug] = React.useState<string | undefined>(undefined);

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const hash = window.location.hash.replace(/^#/, "");
    if (!hash) return;
    if (items.some((it) => it.slug === hash)) {
      setOpenSlug(hash);
      // 한 프레임 뒤에 scroll (아이템 렌더 완료 보장)
      requestAnimationFrame(() => {
        const el = document.getElementById(`faq-${hash}`);
        el?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }, [items]);

  return (
    <Accordion
      type="single"
      collapsible
      value={openSlug}
      onValueChange={(v) => setOpenSlug(v || undefined)}
    >
      {items.map((it) => (
        <AccordionItem key={it.slug} value={it.slug} id={`faq-${it.slug}`}>
          <AccordionTrigger>{it.title}</AccordionTrigger>
          <AccordionContent>
            <div className="editorial-prose" dangerouslySetInnerHTML={{ __html: it.html }} />
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run from `web/`:
```
npx vitest run tests/editorial/ContentAccordion.test.tsx
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add web/components/editorial/ContentAccordion.tsx web/tests/editorial/ContentAccordion.test.tsx
git commit -m "feat(editorial): ContentAccordion — FAQ 단일 펼침 + hash 자동 열기"
```

---

## Task 9: `/glossary` 인덱스 페이지 재구성

**Files:**
- Modify: `web/app/glossary/page.tsx`
- Create: `web/app/glossary/_GlossaryClient.tsx`

- [ ] **Step 1: client 분리 wrapper 작성**

Create `web/app/glossary/_GlossaryClient.tsx`:

```tsx
"use client";
// 글로서리 인덱스의 client 부분 — i18n 텍스트 + 검색·필터 + 카드 렌더.
import { useT } from "@/lib/i18n";
import { ContentCard } from "@/components/editorial/ContentCard";
import { ContentSearchFilter } from "@/components/editorial/ContentSearchFilter";

export interface GlossaryClientItem {
  slug: string;
  title: string;
  excerpt: string;
}

export function GlossaryClient({ items }: { items: GlossaryClientItem[] }) {
  const t = useT();
  return (
    <ContentSearchFilter
      items={items}
      searchPlaceholder={t("glossary.searchPlaceholder")}
      filterAllLabel={t("glossary.filterAll")}
      emptyLabel={t("glossary.empty")}
      renderItem={(it) => (
        <ContentCard
          key={it.slug}
          href={`/glossary/${it.slug}`}
          title={it.title}
          slug={it.slug}
          excerpt={it.excerpt}
          ctaLabel={t("glossary.cardMore")}
        />
      )}
    />
  );
}
```

- [ ] **Step 2: page.tsx 재작성 (server)**

Replace `web/app/glossary/page.tsx`:

```tsx
// 글로서리 인덱스 — Hero + 검색·초성 필터 + 카드 그리드 (server + client wrapper).
import type { Metadata } from "next";

import { getContent, getContentSlugs } from "../../lib/content";
import { Hero } from "@/components/editorial/Hero";
import { GlossaryClient } from "./_GlossaryClient";

const BASE = "https://inkbaduk.com";

export const metadata: Metadata = {
  title: "바둑 용어 — inkbaduk",
  description: "단·급·계가·축·패 등 바둑 용어 해설.",
  alternates: { canonical: `${BASE}/glossary` },
};

export default function GlossaryIndex() {
  const slugs = getContentSlugs("glossary");
  const items = slugs
    .map((s) => getContent("glossary", s))
    .filter((c): c is NonNullable<typeof c> => c !== null)
    .map((c) => ({ slug: c.slug, title: c.title, excerpt: c.excerpt }));

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
      <Hero
        size="compact"
        volume={`VOL. I · 용어`}
        title="바둑 사전"
        subtitle={`KataGo와 두며 만나는 ${items.length}가지 개념`}
      />
      <div className="mt-10">
        <GlossaryClient items={items} />
      </div>
    </div>
  );
}
```

**참고**: subtitle을 i18n 키로 옮기지 않은 이유는 `{count}` 보간을 위한 별도 헬퍼가 i18n에 없을 가능성. 보간 헬퍼가 있으면 `t("glossary.heroSubtitle", { count: items.length })`로 교체. 일단 인라인 — Task 13의 i18n 통합 확인 단계에서 결정.

`useT` placeholder 지원 여부 확인:
```
grep -E "function useT|interpolat" web/lib/i18n.ts web/lib/i18n/index.ts 2>/dev/null | head -10
```
지원하면 i18n 키 사용. 미지원이면 인라인 그대로.

- [ ] **Step 3: build + 라이브 확인 (worktree에서 직접 page는 정적이므로 type-check가 1차)**

Run from `web/`:
```
npm run type-check
npm run lint
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add web/app/glossary/page.tsx web/app/glossary/_GlossaryClient.tsx
git commit -m "feat(glossary): 인덱스 페이지 재구성 — Hero + 검색·초성 + 카드 그리드"
```

---

## Task 10: `/glossary/[slug]` 상세 페이지 재구성

**Files:**
- Modify: `web/app/glossary/[slug]/page.tsx`

- [ ] **Step 1: 헬퍼 함수 결정 + 상세 페이지 작성**

Replace `web/app/glossary/[slug]/page.tsx`:

```tsx
// 글로서리 상세 — Breadcrumb + Hero + editorial-prose 본문 + prev/next + CTA.
import { notFound } from "next/navigation";
import Link from "next/link";

import { getContent, getContentSlugs } from "../../../lib/content";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { Button } from "@/components/ui/button";

interface AdjacentEntry {
  slug: string;
  title: string;
}

function adjacents(currentSlug: string): { prev: AdjacentEntry | null; next: AdjacentEntry | null } {
  const slugs = getContentSlugs("glossary");
  const idx = slugs.indexOf(currentSlug);
  if (idx < 0) return { prev: null, next: null };
  const toEntry = (s: string | undefined): AdjacentEntry | null => {
    if (!s) return null;
    const c = getContent("glossary", s);
    return c ? { slug: c.slug, title: c.title } : null;
  };
  return { prev: toEntry(slugs[idx - 1]), next: toEntry(slugs[idx + 1]) };
}

export default function GlossaryDetail({ params }: { params: { slug: string } }) {
  const c = getContent("glossary", params.slug);
  if (c === null) notFound();
  const { prev, next } = adjacents(params.slug);

  return (
    <article className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <nav className="mb-6 flex items-center gap-2 font-mono text-xs uppercase tracking-label text-ink-faint">
        <Link href="/glossary" className="transition-base hover:text-oxblood">
          용어
        </Link>
        <span aria-hidden>/</span>
        <span className="text-ink-mute">{c.title}</span>
      </nav>

      <Hero
        size="compact"
        volume={c.slug.toUpperCase()}
        title={c.title}
        subtitle={c.excerpt}
      />

      <div
        className="editorial-prose mt-8"
        dangerouslySetInnerHTML={{ __html: c.html }}
      />

      <RuleDivider weight="strong" className="mt-12" />

      <footer className="mt-6 flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row sm:gap-6">
          {prev && (
            <Link
              href={`/glossary/${prev.slug}`}
              className="group flex flex-col gap-1 font-sans text-sm text-ink-mute transition-base hover:text-oxblood"
            >
              <span className="font-mono text-[11px] font-semibold uppercase tracking-label text-ink-faint">
                ← 이전
              </span>
              <span className="font-serif text-base">{prev.title}</span>
            </Link>
          )}
          {next && (
            <Link
              href={`/glossary/${next.slug}`}
              className="group flex flex-col gap-1 font-sans text-sm text-ink-mute transition-base hover:text-oxblood sm:items-end sm:text-right"
            >
              <span className="font-mono text-[11px] font-semibold uppercase tracking-label text-ink-faint">
                다음 →
              </span>
              <span className="font-serif text-base">{next.title}</span>
            </Link>
          )}
        </div>
        <Button asChild>
          <Link href="/game/new">대국 시작 →</Link>
        </Button>
      </footer>
    </article>
  );
}
```

- [ ] **Step 2: 타입·린트**

Run from `web/`:
```
npm run type-check
npm run lint
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add web/app/glossary/\[slug\]/page.tsx
git commit -m "feat(glossary): 상세 페이지 재구성 — Hero + editorial-prose + prev/next + CTA"
```

---

## Task 11: `/faq` 인덱스 페이지 재구성

**Files:**
- Modify: `web/app/faq/page.tsx`
- Create: `web/app/faq/_FaqClient.tsx`

- [ ] **Step 1: client wrapper 작성**

Create `web/app/faq/_FaqClient.tsx`:

```tsx
"use client";
// FAQ 인덱스의 client 부분 — Accordion + 푸터 CTA.
import Link from "next/link";

import { useT } from "@/lib/i18n";
import { ContentAccordion, type AccordionContentItem } from "@/components/editorial/ContentAccordion";

export function FaqClient({ items }: { items: AccordionContentItem[] }) {
  const t = useT();
  return (
    <div className="flex flex-col gap-12">
      <ContentAccordion items={items} />
      <div className="border-t border-ink-faint pt-6 text-center">
        <Link
          href="/support"
          className="font-mono text-xs font-semibold uppercase tracking-label text-oxblood transition-base hover:opacity-80"
        >
          {t("faq.notFoundCta")}
        </Link>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: page.tsx 재작성**

Replace `web/app/faq/page.tsx`:

```tsx
// FAQ 인덱스 — Hero + 단일 펼침 accordion + 푸터 CTA.
import type { Metadata } from "next";

import { getContent, getContentSlugs } from "../../lib/content";
import { Hero } from "@/components/editorial/Hero";
import { FaqClient } from "./_FaqClient";

const BASE = "https://inkbaduk.com";

export const metadata: Metadata = {
  title: "자주 묻는 질문 — inkbaduk",
  description: "inkbaduk의 AI 바둑·복기·세션 등에 대한 자주 묻는 질문.",
  alternates: { canonical: `${BASE}/faq` },
};

export default function FaqIndex() {
  const slugs = getContentSlugs("faq");
  const items = slugs
    .map((s) => getContent("faq", s))
    .filter((c): c is NonNullable<typeof c> => c !== null)
    .map((c) => ({ slug: c.slug, title: c.title, html: c.html }));

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <Hero
        size="compact"
        volume="자주 묻는 질문"
        title="FAQ"
        subtitle={`${items.length}가지 답변`}
      />
      <div className="mt-10">
        <FaqClient items={items} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 타입·린트**

Run from `web/`:
```
npm run type-check
npm run lint
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add web/app/faq/page.tsx web/app/faq/_FaqClient.tsx
git commit -m "feat(faq): 인덱스 페이지 재구성 — Hero + ContentAccordion + 푸터 CTA"
```

---

## Task 12: `/faq/[slug]` 상세 페이지 재구성

**Files:**
- Modify: `web/app/faq/[slug]/page.tsx`

- [ ] **Step 1: page.tsx 재작성**

Replace `web/app/faq/[slug]/page.tsx`:

```tsx
// FAQ 상세 — Breadcrumb + Hero + editorial-prose 본문 + prev/next + CTA (글로서리 상세와 동일 패턴).
import { notFound } from "next/navigation";
import Link from "next/link";

import { getContent, getContentSlugs } from "../../../lib/content";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { Button } from "@/components/ui/button";

interface AdjacentEntry {
  slug: string;
  title: string;
}

function adjacents(currentSlug: string): { prev: AdjacentEntry | null; next: AdjacentEntry | null } {
  const slugs = getContentSlugs("faq");
  const idx = slugs.indexOf(currentSlug);
  if (idx < 0) return { prev: null, next: null };
  const toEntry = (s: string | undefined): AdjacentEntry | null => {
    if (!s) return null;
    const c = getContent("faq", s);
    return c ? { slug: c.slug, title: c.title } : null;
  };
  return { prev: toEntry(slugs[idx - 1]), next: toEntry(slugs[idx + 1]) };
}

export default function FaqDetail({ params }: { params: { slug: string } }) {
  const c = getContent("faq", params.slug);
  if (c === null) notFound();
  const { prev, next } = adjacents(params.slug);

  return (
    <article className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <nav className="mb-6 flex items-center gap-2 font-mono text-xs uppercase tracking-label text-ink-faint">
        <Link href="/faq" className="transition-base hover:text-oxblood">
          FAQ
        </Link>
        <span aria-hidden>/</span>
        <span className="text-ink-mute">{c.title}</span>
      </nav>

      <Hero size="compact" volume="FAQ" title={c.title} subtitle={c.excerpt} />

      <div
        className="editorial-prose mt-8"
        dangerouslySetInnerHTML={{ __html: c.html }}
      />

      <RuleDivider weight="strong" className="mt-12" />

      <footer className="mt-6 flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row sm:gap-6">
          {prev && (
            <Link
              href={`/faq/${prev.slug}`}
              className="group flex flex-col gap-1 font-sans text-sm text-ink-mute transition-base hover:text-oxblood"
            >
              <span className="font-mono text-[11px] font-semibold uppercase tracking-label text-ink-faint">
                ← 이전
              </span>
              <span className="font-serif text-base">{prev.title}</span>
            </Link>
          )}
          {next && (
            <Link
              href={`/faq/${next.slug}`}
              className="group flex flex-col gap-1 font-sans text-sm text-ink-mute transition-base hover:text-oxblood sm:items-end sm:text-right"
            >
              <span className="font-mono text-[11px] font-semibold uppercase tracking-label text-ink-faint">
                다음 →
              </span>
              <span className="font-serif text-base">{next.title}</span>
            </Link>
          )}
        </div>
        <Button asChild>
          <Link href="/game/new">대국 시작 →</Link>
        </Button>
      </footer>
    </article>
  );
}
```

- [ ] **Step 2: 타입·린트**

Run from `web/`:
```
npm run type-check
npm run lint
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add web/app/faq/\[slug\]/page.tsx
git commit -m "feat(faq): 상세 페이지 재구성 — Hero + editorial-prose + prev/next + CTA"
```

---

## Task 13: 전체 검증 + PR + 라이브 활성화

**Files:** 변경 없음 — 검증·배포 단계

- [ ] **Step 1: 전체 type-check + lint**

Run from `web/`:
```
npm run type-check
npm run lint
```
Expected: 둘 다 OK.

- [ ] **Step 2: 전체 vitest 실행**

Run from `web/`:
```
npx vitest run
```
Expected: 신규 테스트 16개(8 excerpt + 8 hangul + 2 ContentCard + 4 SearchFilter + 2 Accordion = 24) 포함 모두 PASS. 기존 테스트 회귀 없음.

- [ ] **Step 3: build 통과 + 모든 라우트 생성**

Run from `web/`:
```
npm run build 2>&1 | tail -30
```
Expected: `/glossary`, `/glossary/[slug]`, `/faq`, `/faq/[slug]` 모두 라우트 표에 나타남. error 없음.

- [ ] **Step 4: branch rename → push → PR**

```bash
git branch -m feat/glossary-faq-redesign
git push -u origin feat/glossary-faq-redesign
gh pr create --title "feat(content): 글로서리·FAQ UI/UX Editorial 재구성 (Encyclopedia + Accordion)" --body "$(cat <<'EOF'
## Summary

글로서리·FAQ 4개 페이지를 Editorial Hardcover 디자인 시스템에 맞춰 재구성.

- 글로서리 인덱스: Hero + 검색 + 한글 초성 chip + 카드 그리드
- 글로서리 상세: Breadcrumb + Hero + editorial-prose + prev/next + CTA
- FAQ 인덱스: Hero + 단일 펼침 Accordion + hash 자동 펼침 + 푸터 CTA
- FAQ 상세: 글로서리 상세와 동일 패턴 (SEO·공유용 유지)

신규: ContentCard, ContentSearchFilter, ContentAccordion (editorial), ui/accordion (shadcn Radix), .editorial-prose CSS, lib/hangul.ts, lib/content.ts.extractExcerpt, i18n 15키.

## Test plan

- [x] vitest: extractExcerpt 8, leadConsonant 8, ContentCard 2, SearchFilter 4, Accordion 2 — 모두 PASS
- [x] type-check + lint OK
- [x] build 4개 라우트 모두 정상
- [ ] **머지 후**: build + web kickstart → 라이브에서 /glossary·/faq·/glossary/chuk·/faq/ai-baduk-vs-human 4 페이지 시각 검증
- [ ] 모바일 폭에서 초성 chip 줄바꿈, accordion 펼침 정상

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 5: 🟡 사람 승인 게이트**

PR 링크 사용자 보고 후 머지 승인 대기. 승인 받기 전 stop.

- [ ] **Step 6: 승인 후 머지 + 라이브 적용**

```bash
gh pr merge --merge --delete-branch
# main worktree 동기화
cd /Users/daegong/projects/baduk && git fetch origin main && git merge --ff-only origin/main
# build + web kickstart
cd web && npm run build 2>&1 | tail -10
launchctl kickstart -k "gui/$(id -u)/com.baduk.web"
sleep 6
# 라이브 verify
for path in /glossary /faq /glossary/chuk /glossary/bik /glossary/dan-gup /faq/ai-baduk-vs-human; do
  printf "  %-40s " "$path"
  curl -fs -o /dev/null -w "%{http_code}\n" --max-time 10 "http://localhost:3000$path"
done
```
Expected: 6 페이지 모두 200.

- [ ] **Step 7: 시각 회귀 (visual-qa 에이전트 별도 디스패치 — 선택)**

`.claude/agents/visual-qa.md`가 정의돼 있으므로 Playwright로 light/dark 4 페이지 캡처 가능. 별도 후속 사이클로.

---

## 자율성 요약

| Task | 등급 |
|---|---|
| 1–12 (코드·테스트) | 🟢 자율 (worktree commits) |
| 13 Step 1-4 (검증 + PR 생성) | 🟢 자율 |
| 13 Step 5 (PR 머지) | 🟡 사람 승인 |
| 13 Step 6 (build + kickstart) | 🟡 (Step 5와 묶어 한 번에 승인) |
| 13 Step 7 (visual-qa) | 🟢 자율 |

## 검증 통과 기준

- 신규 24+ vitest 모두 PASS
- type-check + lint clean
- build 4 라우트 모두 정상 (라우트 표에 표시)
- 라이브 6 URL 200 응답
- 시각: 첫 페인트 Editorial 톤 (font-serif Hero, font-mono uppercase 라벨, oxblood 강조, RuleDivider hairline). prose 톤(Tailwind 기본) 잔존 없음.

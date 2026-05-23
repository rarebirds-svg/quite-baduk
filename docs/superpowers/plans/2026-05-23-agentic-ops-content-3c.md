# Agentic Ops FAQ·용어 해설 LLM 콘텐츠 (하위 프로젝트 3c) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 시드 토픽 15-20개 + 매주 1개 LLM 자율 초안 + Telegram 승인 게시 파이프라인. 마크다운 in-repo, korean-copy-qa 자율 QA.

**Architecture:** 매주 토요일 02:00 launchd가 헤드리스 Claude를 깨워 시드 YAML(`docs/ops/content/seed-*.yml`)에서 미작성 슬러그 1개 선택 → 본문 초안 생성 → `docs/ops/content/drafts/`에 저장 → korean-copy-qa QA → Telegram AP 제안. 승인 답신 시 drafts → `web/content/{glossary,faq}/`로 이동·커밋. Next.js가 `web/content/`를 스캔해 `/glossary/[slug]`·`/faq/[slug]` 라우트 + sitemap에 노출. 3a/3b 패턴 일관.

**Tech Stack:** macOS launchd, 헤드리스 Claude Code(--channels telegram + skip-permissions), `.claude/agents/korean-copy-qa`, YAML 시드(텍스트로 읽음), Next.js 14 App Router + `gray-matter`(frontmatter) + `marked`(md→html) + Vitest.

**브랜치:** 모든 작업은 `feat/agentic-ops-content-3c`에서. spec 커밋 `ce97e8b`가 올라가 있음. base는 `feat/agentic-ops-sre`(3a·3b 머지 후).

**전제:** sub-project 0~3b 머지된 상태. `korean-copy-qa` 에이전트(`.claude/agents/korean-copy-qa.md`) 존재. prod launchd 가동.

**경로 상수:** 리포 루트 `/Users/daegong/projects/baduk`. `claude` `/opt/homebrew/bin/claude`.

**앱 코드 수정**: web에 새 라우트·콘텐츠 디렉터리·sitemap 확장. 검증은 staging에서. prod 반영은 deploy.md.

---

### Task 1: 시드 YAML 2개 + 디렉터리 구조

콘텐츠 토픽 시드와 drafts·published 디렉터리.

**Files:**
- Create: `docs/ops/content/seed-glossary.yml`
- Create: `docs/ops/content/seed-faq.yml`
- Create: `docs/ops/content/drafts/.gitkeep`
- Create: `web/content/glossary/.gitkeep`
- Create: `web/content/faq/.gitkeep`

- [ ] **Step 1: 디렉터리 생성**
```bash
mkdir -p /Users/daegong/projects/baduk/docs/ops/content/drafts
mkdir -p /Users/daegong/projects/baduk/web/content/glossary
mkdir -p /Users/daegong/projects/baduk/web/content/faq
touch /Users/daegong/projects/baduk/docs/ops/content/drafts/.gitkeep
touch /Users/daegong/projects/baduk/web/content/glossary/.gitkeep
touch /Users/daegong/projects/baduk/web/content/faq/.gitkeep
```

- [ ] **Step 2: `docs/ops/content/seed-glossary.yml`** — 그대로:
```yaml
# 글로서리 시드 — slug·title·prompt_hint. LLM이 본문 작성, 사람이 새 항목 추가 시 여기에.
- slug: dan-gup
  title: 단·급
  prompt_hint: 입문~9급 → 1급 → 아마추어 1~7단(또는 9단). 단 차이가 1점 핸디캡에 해당. 한국 바둑 등급 체계.
- slug: gyega
  title: 계가·집
  prompt_hint: 한국 룰의 계가법(territory + 잡은 돌). 종국 절차. 일본 룰과 미세한 차이.
- slug: pae
  title: 패
  prompt_hint: 같은 자리에 즉시 되따냄 금지(동형반복). 패 진행 절차. 패감 개념.
- slug: chuk
  title: 축
  prompt_hint: 직선 추격. 축머리 개념. 축 성립 조건. 초보의 흔한 실수.
- slug: bik
  title: 빅
  prompt_hint: 양쪽 모두 살아 있어 둘 수 없는 상태. 한국 룰의 처리 — 점수 계산 시 빅 안의 집 인정 안 함.
- slug: samsam
  title: 삼삼
  prompt_hint: 3-3 점. 화점에 대한 침입수단. 알파고 이후 정석 변화.
- slug: komi
  title: 덤(komi)
  prompt_hint: 흑 선번 보정. 한국 룰 6.5집(접바둑 0.5집). 일본·중국 룰과 차이.
- slug: handicap
  title: 접바둑·치수
  prompt_hint: 2~9점 접바둑. 흑이 미리 두는 화점 위치. 단 차이만큼 접는 관습.
- slug: hwajeom
  title: 화점
  prompt_hint: 4-4점. 19로 반의 9개 화점 표시. 빠른 세력 확장의 거점.
- slug: kasaeng
  title: 사활
  prompt_hint: 돌의 삶과 죽음. 두 눈의 원칙. 사활 문제는 기력 향상의 핵심.
```

- [ ] **Step 3: `docs/ops/content/seed-faq.yml`** — 그대로:
```yaml
# FAQ 시드 — slug·title(질문)·prompt_hint.
- slug: ai-baduk-vs-human
  title: AI 바둑은 사람과 어떻게 다른가요?
  prompt_hint: KataGo Human-SL — 사람의 기풍을 학습해 자연스러운 수. 일반 KataGo와 차이. 학습 데이터 출처.
- slug: review-and-analysis
  title: 복기·승부처 분석은 무엇인가요?
  prompt_hint: 종국 후 수순 재생 + 매 수의 승률 변화. 승부처(큰 변동 지점) 자동 표시. KataGo 분석.
- slug: nickname-session
  title: 닉네임 세션이란?
  prompt_hint: 이메일·비밀번호 없이 닉네임만으로 임시 세션. HttpOnly 쿠키, 1시간 idle TTL. 개인정보 비수집.
- slug: korean-vs-japanese-rules
  title: 한국 규칙과 일본 규칙의 차이는?
  prompt_hint: 계가법(영토 + 잡은 돌 vs 영토만), 덤(6.5 vs 6.5), 빅·자살 처리 등 미세한 차이.
- slug: how-to-improve-rank
  title: 단을 얻으려면 어떻게 두면 되나요?
  prompt_hint: 정석 학습, 사활 문제, 복기, 실전. 적정 상대와의 대국. 기력 향상 일반 조언.
```

- [ ] **Step 4: `.gitkeep`이 비어 있고 디렉터리 보존되는지 확인**
```bash
find docs/ops/content web/content -type f | sort
```
Expected: 5개 파일 — 2 YAML + 3 .gitkeep.

- [ ] **Step 5: 커밋**
```bash
git add docs/ops/content web/content
git commit -m "feat(content): 시드 YAML 글로서리 10개·FAQ 5개 + 콘텐츠 디렉터리"
```

---

### Task 2: `content-draft-prompt.md` 헤드리스 세션 지시문

매주 launchd가 깨우는 Claude 세션이 따를 절차.

**Files:**
- Create: `docs/ops/content-draft-prompt.md`

- [ ] **Step 1: 프롬프트 작성**

`docs/ops/content-draft-prompt.md`:
```markdown
# 콘텐츠 초안 생성 사이클

너는 inkbaduk의 콘텐츠 초안 생성 세션이다. launchd가 매주 토요일 02:00에 1회 깨운 것이다.
작업 디렉터리는 리포 루트(`/Users/daegong/projects/baduk`)다.

## 시작 전 필수

1. `docs/ops/autonomy-policy.md` — 초안은 🟢 자율, 라이브 게시는 🟡 승인. 게시는 사람 손으로.
2. 출처: 작성한 내용은 공개된 일반 지식 기반. 출처가 불확실하면 본문에 명시.

## 1회 실행

1. **시드 로드** — `docs/ops/content/seed-glossary.yml`과 `seed-faq.yml`을 텍스트로 읽는다. 각 항목은 `{slug, title, prompt_hint}`.

2. **미작성 슬러그 선택** — 우선순위:
   - 글로서리 먼저(아직 `web/content/glossary/<slug>.md`도 `docs/ops/content/drafts/<slug>.md`도 없는 것). 알파벳 순.
   - 글로서리 다 차면 FAQ 동일 규칙.
   - 둘 다 차면 "처리할 토픽 없음" 로그 + 종료.

3. **본문 초안 생성** — 한국어 마크다운, 300-600자, 2-4 단락. frontmatter 포함:
   ```
   ---
   slug: <slug>
   kind: glossary | faq
   title: <title>
   created_at: <YYYY-MM-DD>
   draft_by: agent v1
   ---

   <본문>
   ```
   본문 작성 원칙:
   - 사실 정확성 우선. 모호하면 일반론으로 후퇴.
   - 바둑 용어는 [[korean-copy-qa]] 에이전트의 canonical Korean 용어 따름.
   - 출처 있으면 본문 말미에 "참고: …" 한 줄.

4. **draft 저장** — `docs/ops/content/drafts/<slug>.md`.

5. **korean-copy-qa QA** — `Agent` 도구로 korean-copy-qa 서브에이전트 호출:
   "이 초안의 한국어 자연스러움·바둑 용어 정확성·문체를 점검해 주세요: <draft path>".
   결과 코멘트가 fix 가능한 것이면 본문 수정 반영. 큰 문제면 draft에 "// QA 보류" 코멘트 추가.

6. **AP 제안** — `runbooks/telegram-protocol.md` 형식으로 `state/pending-approvals.md`에 AP 항목 추가:
   - ID: `AP-YYYYMMDD-NN` (NN은 그날 일련번호)
   - 액션: 초안 게시 — `<slug>` ({kind})
   - 영향: `web/content/<kind>/<slug>.md`에 새 파일 + git commit
   - 실행 절차: `mv docs/ops/content/drafts/<slug>.md web/content/<kind>/<slug>.md && git add web/content/<kind>/<slug>.md && git commit -m "content(<kind>): <slug> 게시"`
   Telegram으로 같은 내용 전송.

7. **로그·기록** — `state/log/YYYY-MM-DD.md`에 한 줄. 1주기 1개 한정.

## 끝낼 때

한 일을 2~3줄로 요약하고 종료. 이 세션은 1회성이다.
```

- [ ] **Step 2: 커밋**
```bash
git add docs/ops/content-draft-prompt.md
git commit -m "feat(content): content-draft 헤드리스 세션 지시문"
```

---

### Task 3: `content-draft` launchd + 래퍼

매주 토요일 02:00 헤드리스 Claude를 깨우는 launchd.

**Files:**
- Create: `ops/run-content-draft.sh`
- Create: `ops/launchd/com.inkbaduk.content-draft.plist`

- [ ] **Step 1: `ops/run-content-draft.sh`**:
```bash
#!/usr/bin/env bash
# launchd가 매주 토요일 02:00 호출 — 콘텐츠 초안 헤드리스 Claude를 1회 실행.
set -euo pipefail
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"

[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }

mkdir -p docs/ops/state/log
RUNLOG="docs/ops/state/log/content-draft-runs.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] content-draft 시작" >> "$RUNLOG"

/opt/homebrew/bin/claude -p "$(cat docs/ops/content-draft-prompt.md)" \
  --dangerously-skip-permissions \
  --channels plugin:telegram@claude-plugins-official \
  >> "$RUNLOG" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] content-draft 종료" >> "$RUNLOG"
```

- [ ] **Step 2: 실행 권한**
`chmod +x /Users/daegong/projects/baduk/ops/run-content-draft.sh`

- [ ] **Step 3: `ops/launchd/com.inkbaduk.content-draft.plist`**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- 매주 토요일 02:00 콘텐츠 초안 생성을 실행하는 launchd 작업. -->
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.inkbaduk.content-draft</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/daegong/projects/baduk/ops/run-content-draft.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>6</integer>
    <key>Hour</key><integer>2</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/content-draft.out.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/content-draft.err.log</string>
</dict>
</plist>
```
(macOS launchd `Weekday` — 일=0/7, 월=1, 화=2, 수=3, 목=4, 금=5, **토=6**.)

- [ ] **Step 4: 등록**
```bash
cp /Users/daegong/projects/baduk/ops/launchd/com.inkbaduk.content-draft.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.inkbaduk.content-draft.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.inkbaduk.content-draft.plist
launchctl list | grep com.inkbaduk.content-draft
```
Expected: 등록.

- [ ] **Step 5: 검사**
```bash
bash -n /Users/daegong/projects/baduk/ops/run-content-draft.sh && echo "shell OK"
plutil -lint /Users/daegong/projects/baduk/ops/launchd/com.inkbaduk.content-draft.plist
xmllint --noout /Users/daegong/projects/baduk/ops/launchd/com.inkbaduk.content-draft.plist && echo "xml OK"
```

- [ ] **Step 6: 커밋**
```bash
git add ops/run-content-draft.sh ops/launchd/com.inkbaduk.content-draft.plist
git commit -m "feat(ops): content-draft launchd (토요일 02:00)"
```

이 태스크에서 `launchctl start` 트리거 금지 — Task 8 검증에서 1회 실행.

---

### Task 4: `web/lib/content.ts` 마크다운 reader + 의존성

`gray-matter` + `marked` 추가, `web/content/<kind>/<slug>.md` 읽기·렌더 헬퍼.

**Files:**
- Create: `web/lib/content.ts`
- Create: `web/tests/content.test.ts`
- Modify: `web/package.json` (deps 추가)
- Create: `web/content/glossary/dan-gup.md` (샘플)
- Create: `web/content/faq/ai-baduk-vs-human.md` (샘플)

- [ ] **Step 1: 의존성 추가**

Run:
```bash
cd /Users/daegong/projects/baduk/web
npm install gray-matter marked
```
설치 후 `package.json` `dependencies`에 두 항목 자동 추가. `package-lock.json`도 갱신됨.

- [ ] **Step 2: 샘플 콘텐츠 작성**

`web/content/glossary/dan-gup.md`:
```markdown
---
slug: dan-gup
kind: glossary
title: 단·급
created_at: 2026-05-23
draft_by: hand
---

단·급은 바둑 실력을 표시하는 등급 체계입니다.

입문자는 18급에서 시작해 한 단계씩 올라가 1급에 이르고, 그 위로 아마추어 1단부터
7단(공식 단증 기준 9단까지)으로 이어집니다. 단의 차이는 대국에서 핸디캡 한 점에
해당해 — 1단 차이는 1점 접바둑이 표준입니다.

한국 바둑은 한국기원 단증을 발급하며, AI 바둑 같은 온라인 환경에서는 별도의 내부
레이팅을 단·급으로 환산해 표시합니다.
```

`web/content/faq/ai-baduk-vs-human.md`:
```markdown
---
slug: ai-baduk-vs-human
kind: faq
title: AI 바둑은 사람과 어떻게 다른가요?
created_at: 2026-05-23
draft_by: hand
---

inkbaduk이 쓰는 KataGo Human-SL 모델은 일반 KataGo와 다릅니다.

일반 KataGo는 자기 학습으로 최적해에 가까운 수를 두지만, Human-SL은 인간의 실전
대국을 학습해 **사람다운 기풍**으로 둡니다. 입문자에게는 입문자처럼, 강한 사람에게는
강한 사람처럼 — 단지 약한 게 아니라 자연스럽게 둡니다.

복기와 분석은 일반 KataGo로 돌아가 정확한 평가를 제공합니다 — 대국은 사람처럼,
분석은 객관적으로.
```

- [ ] **Step 3: 실패 테스트**

`web/tests/content.test.ts`:
```ts
// 마크다운 콘텐츠 reader 테스트 — 실제 web/content/ 디렉터리의 샘플 파일을 fixture로.
import { describe, it, expect } from "vitest";
import { getContentSlugs, getContent } from "../lib/content";

describe("content", () => {
  it("getContentSlugs lists glossary slugs", () => {
    const slugs = getContentSlugs("glossary");
    expect(slugs).toContain("dan-gup");
  });

  it("getContentSlugs lists faq slugs", () => {
    const slugs = getContentSlugs("faq");
    expect(slugs).toContain("ai-baduk-vs-human");
  });

  it("getContent returns metadata + html for glossary", () => {
    const c = getContent("glossary", "dan-gup");
    expect(c).not.toBeNull();
    expect(c!.slug).toBe("dan-gup");
    expect(c!.title).toBe("단·급");
    expect(c!.kind).toBe("glossary");
    expect(c!.html).toContain("<p>");
    expect(c!.html).toContain("단·급은");
  });

  it("getContent returns null for missing slug", () => {
    expect(getContent("glossary", "does-not-exist")).toBeNull();
  });

  it("getContent returns null for unknown kind", () => {
    expect(getContent("glossary", "ai-baduk-vs-human")).toBeNull(); // wrong kind
  });
});
```

- [ ] **Step 4: 실패 확인**

Run: `cd web && npm test -- --run content.test`
Expected: FAIL (import resolves to nothing, getContentSlugs/getContent undefined).

- [ ] **Step 5: 구현**

`web/lib/content.ts`:
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

export function getContent(kind: ContentKind, slug: string): ContentItem | null {
  const file = path.join(contentDir(kind), `${slug}.md`);
  if (!fs.existsSync(file)) return null;
  const raw = fs.readFileSync(file, "utf-8");
  const { data, content } = matter(raw);
  if (data.kind !== kind) return null;
  if (data.slug !== slug) return null;
  const html = marked.parse(content, { async: false }) as string;
  return {
    slug,
    kind,
    title: String(data.title ?? slug),
    created_at: data.created_at ? String(data.created_at) : undefined,
    html,
  };
}
```

- [ ] **Step 6: 테스트 통과**

Run: `cd web && npm test -- --run content.test`
Expected: 5개 PASS.

- [ ] **Step 7: 회귀 + 빌드**
```bash
npm run lint
npm run type-check
npm test -- --run 2>&1 | tail -3
```
Expected: 통과.

- [ ] **Step 8: 커밋**
```bash
git add web/lib/content.ts web/tests/content.test.ts web/content/glossary/dan-gup.md web/content/faq/ai-baduk-vs-human.md web/package.json web/package-lock.json
git commit -m "feat(web): 마크다운 콘텐츠 reader (lib/content.ts) + gray-matter·marked deps + 샘플 2개"
```

---

### Task 5: 글로서리 라우트

`/glossary` 인덱스 + `/glossary/[slug]` 상세 + layout.

**Files:**
- Create: `web/app/glossary/page.tsx`
- Create: `web/app/glossary/[slug]/page.tsx`
- Create: `web/app/glossary/[slug]/layout.tsx`

- [ ] **Step 1: 인덱스 페이지**

`web/app/glossary/page.tsx`:
```tsx
// 글로서리 인덱스 — web/content/glossary/ 디렉터리의 모든 슬러그 리스트.
import type { Metadata } from "next";

import { getContent, getContentSlugs } from "../../lib/content";

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
    .filter((c): c is NonNullable<typeof c> => c !== null);
  return (
    <article className="prose">
      <h1>바둑 용어</h1>
      <p>총 {items.length}개 항목.</p>
      <ul className="not-prose grid gap-1">
        {items.map((c) => (
          <li key={c.slug}>
            <a href={`/glossary/${c.slug}`}>{c.title}</a>
          </li>
        ))}
      </ul>
    </article>
  );
}
```

- [ ] **Step 2: 상세 페이지**

`web/app/glossary/[slug]/page.tsx`:
```tsx
// 글로서리 상세 페이지 — 마크다운 본문을 server-side 렌더.
import { notFound } from "next/navigation";

import { getContent } from "../../../lib/content";

export default function GlossaryDetail({
  params,
}: {
  params: { slug: string };
}) {
  const c = getContent("glossary", params.slug);
  if (c === null) notFound();
  return (
    <article className="prose">
      <header>
        <h1>{c.title}</h1>
      </header>
      <div dangerouslySetInnerHTML={{ __html: c.html }} />
    </article>
  );
}
```

- [ ] **Step 3: layout (generateMetadata)**

`web/app/glossary/[slug]/layout.tsx`:
```tsx
// 글로서리 상세 페이지 SEO 메타.
import type { Metadata } from "next";
import type { ReactNode } from "react";

import { getContent } from "../../../lib/content";

const BASE = "https://inkbaduk.com";

export function generateMetadata(
  { params }: { params: { slug: string } },
): Metadata {
  const c = getContent("glossary", params.slug);
  if (c === null) return { robots: { index: false, follow: false } };
  const title = `${c.title} — inkbaduk 바둑 용어`;
  const description = `바둑 용어 "${c.title}" 해설.`;
  const canonical = `${BASE}/glossary/${c.slug}`;
  return {
    title,
    description,
    alternates: { canonical },
    openGraph: { title, description, url: canonical },
  };
}

export default function GlossaryLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
```

- [ ] **Step 4: 빌드 + 타입**

Run:
```bash
cd web
npm run type-check
npm run build 2>&1 | tail -8
```
Expected: 통과, `/glossary` Static + `/glossary/[slug]` Dynamic 등록.

- [ ] **Step 5: 커밋**
```bash
git add web/app/glossary
git commit -m "feat(web): /glossary 인덱스 + [slug] 상세 + generateMetadata"
```

---

### Task 6: FAQ 라우트

Task 5와 동일 패턴.

**Files:**
- Create: `web/app/faq/page.tsx`
- Create: `web/app/faq/[slug]/page.tsx`
- Create: `web/app/faq/[slug]/layout.tsx`

- [ ] **Step 1: 인덱스**

`web/app/faq/page.tsx`:
```tsx
// FAQ 인덱스 — web/content/faq/의 모든 슬러그.
import type { Metadata } from "next";

import { getContent, getContentSlugs } from "../../lib/content";

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
    .filter((c): c is NonNullable<typeof c> => c !== null);
  return (
    <article className="prose">
      <h1>자주 묻는 질문</h1>
      <p>총 {items.length}개 질문.</p>
      <ul className="not-prose grid gap-1">
        {items.map((c) => (
          <li key={c.slug}>
            <a href={`/faq/${c.slug}`}>{c.title}</a>
          </li>
        ))}
      </ul>
    </article>
  );
}
```

- [ ] **Step 2: 상세**

`web/app/faq/[slug]/page.tsx`:
```tsx
// FAQ 상세 — 마크다운 본문을 server-side 렌더.
import { notFound } from "next/navigation";

import { getContent } from "../../../lib/content";

export default function FaqDetail({
  params,
}: {
  params: { slug: string };
}) {
  const c = getContent("faq", params.slug);
  if (c === null) notFound();
  return (
    <article className="prose">
      <header>
        <h1>{c.title}</h1>
      </header>
      <div dangerouslySetInnerHTML={{ __html: c.html }} />
    </article>
  );
}
```

- [ ] **Step 3: layout**

`web/app/faq/[slug]/layout.tsx`:
```tsx
// FAQ 상세 페이지 SEO 메타.
import type { Metadata } from "next";
import type { ReactNode } from "react";

import { getContent } from "../../../lib/content";

const BASE = "https://inkbaduk.com";

export function generateMetadata(
  { params }: { params: { slug: string } },
): Metadata {
  const c = getContent("faq", params.slug);
  if (c === null) return { robots: { index: false, follow: false } };
  const title = `${c.title} — inkbaduk FAQ`;
  const description = c.title;
  const canonical = `${BASE}/faq/${c.slug}`;
  return {
    title,
    description,
    alternates: { canonical },
    openGraph: { title, description, url: canonical },
  };
}

export default function FaqLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
```

- [ ] **Step 4: 빌드**
```bash
cd web && npm run type-check && npm run build 2>&1 | tail -5
```
Expected: 통과.

- [ ] **Step 5: 커밋**
```bash
git add web/app/faq
git commit -m "feat(web): /faq 인덱스 + [slug] 상세 + generateMetadata"
```

---

### Task 7: sitemap.ts 확장 + 테스트

글로서리·FAQ URL을 sitemap에 추가.

**Files:**
- Modify: `web/app/sitemap.ts`
- Modify: `web/tests/sitemap.test.ts`

- [ ] **Step 1: 실패 테스트**

`web/tests/sitemap.test.ts` 끝에 추가:
```ts
describe("sitemap glossary and faq", () => {
  it("includes glossary + faq slug URLs from content directory", async () => {
    // sitemap.ts가 web/content/<kind>/를 스캔. 실제 dan-gup·ai-baduk-vs-human이 있어야.
    const { default: sitemap } = await import("../app/sitemap");
    const urls = await sitemap();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/glossary")).toBeDefined();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/glossary/dan-gup")).toBeDefined();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/faq")).toBeDefined();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/faq/ai-baduk-vs-human")).toBeDefined();
  });
});
```

- [ ] **Step 2: 실패 확인**
Run: `cd web && npm test -- --run sitemap.test`
Expected: 새 테스트 FAIL, 기존 통과.

- [ ] **Step 3: sitemap.ts 확장**

`web/app/sitemap.ts` 상단 import 다음 줄에 추가:
```ts
import { getContentSlugs } from "../lib/content";
```

기존 `monthlyPickMonths()` 함수 다음에 추가:
```ts
function contentUrls(kind: "glossary" | "faq"): MetadataRoute.Sitemap {
  const slugs = getContentSlugs(kind);
  return [
    {
      url: `${BASE}/${kind}`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.5,
    },
    ...slugs.map((s) => ({
      url: `${BASE}/${kind}/${s}`,
      lastModified: new Date(),
      changeFrequency: "monthly" as const,
      priority: 0.5,
    })),
  ];
}
```

기존 `return [...staticUrls, ...proUrls, ...themeUrls, ...picksIndex, ...pickUrls];`를 다음으로 교체:
```ts
  const glossaryUrls = contentUrls("glossary");
  const faqUrls = contentUrls("faq");
  return [
    ...staticUrls,
    ...proUrls,
    ...themeUrls,
    ...picksIndex,
    ...pickUrls,
    ...glossaryUrls,
    ...faqUrls,
  ];
```

- [ ] **Step 4: 테스트 통과**
Run: `cd web && npm test -- --run sitemap.test`
Expected: 모든 sitemap 테스트(4개 — 기존 3 + 신규 1) PASS.

- [ ] **Step 5: 회귀 + 린트**
```bash
npm run lint
npm run type-check
npm run build 2>&1 | tail -5
```
Expected: 통과.

- [ ] **Step 6: 커밋**
```bash
git add web/app/sitemap.ts web/tests/sitemap.test.ts
git commit -m "feat(web): sitemap에 글로서리·FAQ URL 추가"
```

---

### Task 8: 통합 검증 + 대시보드 + content-draft 1회 트리거

검증 기준 4가지 일괄 확인.

**Files:**
- Modify: `docs/ops/state/dashboard.md`
- Modify: `docs/ops/state/log/2026-05-23.md`

- [ ] **Step 1: staging worktree 3c 코드로 갱신**
```bash
cd /Users/daegong/projects/baduk
git -C .worktrees/staging fetch
git -C .worktrees/staging checkout --detach feat/agentic-ops-content-3c
# staging은 sub-project 2 이후 자체 실제 node_modules 보유. 새 deps 동기화:
cd /Users/daegong/projects/baduk/.worktrees/staging/web
npm install
cd /Users/daegong/projects/baduk
ops/stack.sh down staging 2>/dev/null || true
ops/stack.sh up staging
sleep 60
```
(심볼릭 링크로 되돌리지 말 것 — sub-project 2 AP-20260523-01의 prod 502 장애 원인이었음.)

- [ ] **Step 2: 검증 기준 #1 — 시드 YAML**
```bash
grep -c '^- slug:' docs/ops/content/seed-glossary.yml
grep -c '^- slug:' docs/ops/content/seed-faq.yml
```
Expected: 글로서리 10, FAQ 5. 합 ≥15.

- [ ] **Step 3: 검증 기준 #2 — content-draft launchd 등록 + 수동 트리거**
```bash
launchctl list | grep com.inkbaduk.content-draft
launchctl start com.inkbaduk.content-draft
sleep 90
tail -40 docs/ops/state/log/content-draft-runs.log
```
Expected: 등록 + 시작/종료 로그. drafts/에 새 파일 생성 OR "처리할 토픽 없음".
글로서리 10개 중 1개(`dan-gup`)만 published 상태라 9개 미작성 — agent가 다른 슬러그 1개 초안 생성해야 정상. 또는 AP가 `pending-approvals.md`에 등록됨.

확인:
```bash
ls docs/ops/content/drafts/
cat docs/ops/state/pending-approvals.md | grep AP-
```

- [ ] **Step 4: 검증 기준 #3 — 게시 흐름 시뮬레이션**

(수동 승인 절차 시연 — Task 8 실행자가 한 번 처리해 봄. 실제 운영 시는 사용자가 Telegram으로 답신.)

`docs/ops/content/drafts/`에 파일이 있으면 (예: `dan-gup` 이외의 슬러그) 그 중 하나를 골라 `web/content/<kind>/<slug>.md`로 옮기고 git commit:
```bash
DRAFT_FILE=$(ls docs/ops/content/drafts/*.md 2>/dev/null | head -1)
if [ -n "$DRAFT_FILE" ]; then
  SLUG=$(basename "$DRAFT_FILE" .md)
  KIND=$(grep '^kind:' "$DRAFT_FILE" | awk '{print $2}')
  mv "$DRAFT_FILE" "web/content/$KIND/$SLUG.md"
  git add "web/content/$KIND/$SLUG.md" "docs/ops/content/drafts/" 2>/dev/null
  git commit -m "content($KIND): $SLUG 게시 (검증)" 2>/dev/null || echo "이미 커밋됨"
fi
```

drafts/가 비어 있어도 검증은 진행 — 샘플 `dan-gup`·`ai-baduk-vs-human`로 라우트 동작 확인.

- [ ] **Step 5: staging 재기동 (콘텐츠 반영)**
```bash
cd /Users/daegong/projects/baduk
git -C .worktrees/staging fetch
git -C .worktrees/staging checkout --detach feat/agentic-ops-content-3c
ops/stack.sh down staging
ops/stack.sh up staging
sleep 45
```

- [ ] **Step 6: 검증 기준 #4 — 라우트 + sitemap**
```bash
echo "--- 글로서리 인덱스 ---"
curl -fs -o /dev/null -w "HTTP %{http_code}\n" http://localhost:3100/glossary
echo "--- 글로서리 상세(dan-gup) ---"
curl -fs http://localhost:3100/glossary/dan-gup | grep -oE '<title>[^<]+</title>|<link rel="canonical" href="[^"]+"' | head -2
echo "--- FAQ 인덱스 ---"
curl -fs -o /dev/null -w "HTTP %{http_code}\n" http://localhost:3100/faq
echo "--- FAQ 상세 ---"
curl -fs http://localhost:3100/faq/ai-baduk-vs-human | grep -oE '<title>[^<]+</title>|<link rel="canonical" href="[^"]+"' | head -2
echo "--- sitemap ---"
SITEMAP=$(curl -fs http://localhost:3100/sitemap.xml)
echo "glossary URL: $(echo "$SITEMAP" | grep -c '/glossary')"
echo "faq URL: $(echo "$SITEMAP" | grep -c '/faq')"
```
Expected: 4개 페이지 200 + 고유 title·canonical + sitemap에 글로서리·FAQ URL 포함.

- [ ] **Step 7: prod 무손상**
```bash
curl -fs http://localhost:8000/api/health && echo " prod-backend OK"
curl -fs http://localhost:3000 >/dev/null && echo "prod-web OK"
```

- [ ] **Step 8: 대시보드 + 로그 갱신**

`docs/ops/state/dashboard.md`의 `## 콘텐츠 인덱스` 섹션 갱신 — 글로서리·FAQ 항목 추가:
```
| 글로서리 | <published>/10 |
| FAQ | <published>/5 |
| sitemap 글로서리·FAQ URL | <count> |
```
실측값으로 채움. published 개수는 `ls web/content/glossary/ | grep -c '.md'` 등으로 확인.

`docs/ops/state/log/2026-05-23.md`에 추가:
```
## <현재시각> — FAQ·용어 해설(sub-project 3c) 구축 완료
- 검증 기준 4/4 통과: ① 시드 YAML ② content-draft launchd + 트리거 ③ 게시 흐름 ④ 라우트·sitemap
- staging 검증 완료. prod 반영은 별도 deploy.md 절차.
```

- [ ] **Step 9: 커밋**
```bash
git add docs/ops/state
git commit -m "feat(ops): FAQ·용어 해설 구축 완료 — 검증 기준 4/4 통과"
```

- [ ] **Step 10: 최종 보고**

---

## 검증 기준 (spec)

1. 시드 YAML 2개 + 초기 시드 ≥15개. → Task 1, 8
2. `com.inkbaduk.content-draft` launchd 등록 + 수동 트리거 초안 생성·AP 도달. → Task 3, 8
3. 승인 흐름 시뮬레이션 — drafts → web/content/ 이동 + git commit. → Task 2(절차 정의), 8(시연)
4. 라우트 + sitemap 동작 — `/glossary`·`/faq` 200, 메타 고유, sitemap 포함. → Task 4·5·6·7·8

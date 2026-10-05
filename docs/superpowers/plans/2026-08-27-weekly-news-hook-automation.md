# 주간 속보 훅 자동화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 홈 랜딩의 NewsHook을 일회성 수동 배너에서, 바둑·프로기사·AI 대국 관련 화제성 뉴스를 매주 자동 탐색해 갱신하는 파이프라인으로 바꾼다.

**Architecture:** NewsHook 문구를 정적 i18n 번들에서 `web/content/news-hook.json` 동적 파일로 옮겨 재빌드 없이 반영되게 하고, 별도 launchd job(`ops/run-news-hook.sh` + `docs/ops/news-hook-prompt.md`)이 주 1회 WebSearch→게이트→생성→사실검증→게시 5단계를 헤드리스 Claude로 수행한다. `content-draft`와 완전히 독립된 병렬 job.

**Tech Stack:** Next.js 14 App Router(서버 컴포넌트 fs read), Vitest, launchd, 헤드리스 `claude -p --dangerously-skip-permissions`.

**Spec:** [docs/superpowers/specs/2026-08-27-weekly-news-hook-automation-design.md](../specs/2026-08-27-weekly-news-hook-automation-design.md)

## Global Constraints

- 기사 원문 인용 금지 — 사실만 자기 문장으로 재서술한다.
- 출처 URL 없는 항목은 게시하지 않는다.
- 이번 주 게시할 만한 뉴스가 없으면 **현재 문구를 그대로 유지**한다 — 소재를 지어내지 않는다.
- 도메인 범위는 바둑·프로기사·AI-vs-인간 대국으로 한정한다(일반 AI 산업 뉴스 제외).
- 새 파일 헤더는 한국어 한 줄 주석(AGENTS.md 규칙 6) — `.ts`/`.tsx`는 `//`, `.sh`는 `#`.
- **사전 검증 완료**: 헤드리스 `claude -p --dangerously-skip-permissions` 세션에서 WebSearch 도구가 실제로 동작함을 스파이크로 확인함(2026-08-27, 실제 기사 URL 3건 반환). 대체 경로(firecrawl 등) 불필요.

---

### Task 1: `news-hook.json` 로더 + 시드 파일

**Files:**
- Create: `web/content/news-hook.json`
- Create: `web/lib/newsHook.ts`
- Test: `web/tests/newsHook.test.ts`

**Interfaces:**
- Produces: `export interface NewsHookData { updated_at: string; source_url: string; body_ko: string; body_en: string; guide_ko: string; guide_en: string }`, `export function getNewsHook(): NewsHookData | null`

- [ ] **Step 1: 시드 파일 작성 — 기존 신진서-카타고 문구를 그대로 옮긴다**

`web/content/news-hook.json`:
```json
{
  "updated_at": "2026-07-21",
  "source_url": "https://news.sbs.co.kr/news/endPage.do?news_id=N1008664048",
  "body_ko": "인류가 현존 최강 AI를 다시 넘어섰습니다. 신진서 9단이 2점 접바둑 3번기에서 카타고를 2승 1패로 꺾었죠. 그 카타고(Human-SL)가 지금 잉크바둑에서 당신을 기다립니다.",
  "body_en": "Humanity just edged the strongest AI alive — 9-dan Shin Jinseo beat KataGo 2–1 in a three-game match at a two-stone handicap. That same KataGo (Human-SL) is waiting for you on Inkbaduk.",
  "guide_ko": "닉네임만 입력하면 바로 그 AI와 한 판이 시작됩니다.",
  "guide_en": "Enter a nickname and take on that very AI."
}
```
(`source_url`은 2026-07-21 스펙 문서의 레퍼런스 보도를 사용 — 실제 SBS 기사 URL로, 위 WebSearch 스파이크 결과에서도 동일 URL이 확인됨.)

- [ ] **Step 2: 실패하는 테스트 작성**

`web/tests/newsHook.test.ts`:
```ts
// news-hook.json 로더가 실제 시드 파일을 올바르게 읽는지 검증한다.
import { describe, it, expect } from "vitest";
import { getNewsHook } from "../lib/newsHook";

describe("getNewsHook", () => {
  it("시드 파일의 필드를 그대로 반환한다", () => {
    const data = getNewsHook();
    expect(data).not.toBeNull();
    expect(data!.source_url).toBe(
      "https://news.sbs.co.kr/news/endPage.do?news_id=N1008664048",
    );
    expect(data!.body_ko).toContain("신진서");
    expect(data!.body_en).toContain("Shin Jinseo");
    expect(data!.guide_ko).toContain("닉네임");
    expect(typeof data!.updated_at).toBe("string");
  });
});
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd web && npm test -- --run tests/newsHook.test.ts`
Expected: FAIL — `Cannot find module '../lib/newsHook'`

- [ ] **Step 4: 로더 구현**

`web/lib/newsHook.ts`:
```ts
// 홈 랜딩 속보 훅 데이터를 web/content/news-hook.json에서 읽는 서버 전용 로더.
import fs from "node:fs";
import path from "node:path";

const NEWS_HOOK_PATH = path.join(process.cwd(), "content", "news-hook.json");

export interface NewsHookData {
  updated_at: string;
  source_url: string;
  body_ko: string;
  body_en: string;
  guide_ko: string;
  guide_en: string;
}

export function getNewsHook(): NewsHookData | null {
  if (!fs.existsSync(NEWS_HOOK_PATH)) return null;
  const raw = fs.readFileSync(NEWS_HOOK_PATH, "utf-8");
  return JSON.parse(raw) as NewsHookData;
}
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd web && npm test -- --run tests/newsHook.test.ts`
Expected: PASS (1 test)

- [ ] **Step 6: 커밋**

```bash
git add web/content/news-hook.json web/lib/newsHook.ts web/tests/newsHook.test.ts
git commit -m "feat(web): news-hook.json 동적 로더 추가"
```

---

### Task 2: `NewsHook.tsx`를 data prop 기반으로 전환

**Files:**
- Modify: `web/components/editorial/NewsHook.tsx`
- Test: `web/tests/editorial/NewsHook.test.tsx`

**Interfaces:**
- Consumes: `NewsHookData` (Task 1), `useLocale` from `@/lib/i18n` (기존)
- Produces: `export function NewsHook(props: { data: NewsHookData | null }): JSX.Element | null`

- [ ] **Step 1: 실패하는 테스트 작성**

`web/tests/editorial/NewsHook.test.tsx`:
```tsx
// NewsHook이 data prop을 로케일에 맞게 렌더링하는지 검증한다.
import { describe, it, expect, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { NewsHook } from "@/components/editorial/NewsHook";
import { setLocale } from "@/lib/i18n";
import type { NewsHookData } from "@/lib/newsHook";

const SAMPLE: NewsHookData = {
  updated_at: "2026-08-27",
  source_url: "https://example.com/article",
  body_ko: "한국어 본문",
  body_en: "English body",
  guide_ko: "한국어 안내",
  guide_en: "English guide",
};

afterEach(() => setLocale("ko"));

describe("NewsHook", () => {
  it("data가 없으면 아무것도 렌더링하지 않는다", () => {
    const { container } = render(<NewsHook data={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("한국어 로케일에서 ko 필드를 보여준다", () => {
    setLocale("ko");
    render(<NewsHook data={SAMPLE} />);
    expect(screen.getByText("한국어 본문")).toBeInTheDocument();
    expect(screen.getByText("한국어 안내")).toBeInTheDocument();
  });

  it("영어 로케일에서 en 필드를 보여준다", () => {
    setLocale("en");
    render(<NewsHook data={SAMPLE} />);
    expect(screen.getByText("English body")).toBeInTheDocument();
    expect(screen.getByText("English guide")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd web && npm test -- --run tests/editorial/NewsHook.test.tsx`
Expected: FAIL — `data` prop이 없어 타입 에러 또는 `SAMPLE.body_ko` 텍스트 미발견

- [ ] **Step 3: 컴포넌트 수정**

`web/components/editorial/NewsHook.tsx` 전체를 다음으로 교체:
```tsx
"use client";
// 홈 랜딩 히어로용 타임리 뉴스 훅 — 화제성 뉴스 유입을 대국 시작으로 전환.
// 본문(body/guide)은 web/content/news-hook.json에서 매주 자동 갱신된다(kicker만 i18n 고정 라벨).
import { ArrowDown, Newspaper } from "lucide-react";
import { useT, useLocale } from "@/lib/i18n";
import type { NewsHookData } from "@/lib/newsHook";

export function NewsHook({ data }: { data: NewsHookData | null }) {
  const t = useT();
  const [locale] = useLocale();
  if (!data) return null;
  const body = locale === "ko" ? data.body_ko : data.body_en;
  const guide = locale === "ko" ? data.guide_ko : data.guide_en;
  return (
    <div className="mt-8 flex items-start gap-3 border border-oxblood/30 rounded-sm bg-oxblood/5 px-5 py-4">
      <Newspaper size={16} strokeWidth={1.5} className="mt-0.5 shrink-0 text-oxblood" aria-hidden="true" />
      <div className="flex flex-col gap-2">
        <p className="font-sans text-sm leading-relaxed text-ink">
          <span className="font-semibold uppercase tracking-widest text-xs text-oxblood mr-2">
            {t("home.newsHook.kicker")}
          </span>
          {body}
        </p>
        <p className="flex items-center gap-1.5 font-sans text-sm text-ink-mute">
          <ArrowDown size={16} strokeWidth={1.5} className="shrink-0" aria-hidden="true" />
          {guide}
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd web && npm test -- --run tests/editorial/NewsHook.test.tsx`
Expected: PASS (3 tests)

- [ ] **Step 5: 커밋**

```bash
git add web/components/editorial/NewsHook.tsx web/tests/editorial/NewsHook.test.tsx
git commit -m "feat(web): NewsHook을 data prop 기반으로 전환"
```

---

### Task 3: 서버→클라이언트 데이터 배선 + 구 i18n 키 제거

**Files:**
- Modify: `web/app/page.tsx`
- Modify: `web/app/_HomeLanding.tsx`
- Modify: `web/lib/i18n/ko.json`
- Modify: `web/lib/i18n/en.json`

**Interfaces:**
- Consumes: `getNewsHook` (Task 1), `NewsHook` (Task 2)

- [ ] **Step 1: `page.tsx`에서 서버 사이드로 데이터를 읽어 전달**

`web/app/page.tsx` 전체를 다음으로 교체:
```tsx
// 홈 라우트 — 서버에서 메타데이터와 속보 훅 데이터를 확정하고 본문은 클라이언트 랜딩 조각에 위임한다.
import type { Metadata } from "next";

import { getNewsHook } from "@/lib/newsHook";
import HomeLanding from "./_HomeLanding";

export const metadata: Metadata = {
  // 루트 layout의 template이 덧붙지 않도록 absolute로 고정 — 지금 노출 중인 제목 그대로다.
  title: { absolute: "Inkbaduk · 조용한 승부" },
  description:
    "닉네임 한 줄로 바로 시작하는 무료 AI 바둑. KataGo Human-SL이 9급부터 9단까지 사람처럼 두고, 대국이 끝나면 승부처를 복기합니다.",
  alternates: { canonical: "/" },
};

export default function HomePage() {
  return <HomeLanding newsHook={getNewsHook()} />;
}
```

- [ ] **Step 2: `_HomeLanding.tsx`가 prop을 받아 전달하도록 수정**

`web/app/_HomeLanding.tsx`의 import·시그니처·렌더 지점 3곳을 수정한다:

```tsx
import { NewsHook } from "@/components/editorial/NewsHook";
import type { NewsHookData } from "@/lib/newsHook";
```
(기존 `import { NewsHook } ...` 줄 바로 아래에 타입 import 추가)

```tsx
export default function HomeLanding({ newsHook }: { newsHook: NewsHookData | null }) {
```
(기존 `export default function HomeLanding() {` 교체)

```tsx
        <NewsHook data={newsHook} />
```
(기존 `<NewsHook />` 교체)

- [ ] **Step 3: 구 i18n 키 제거 — body/guide만, kicker는 유지**

`web/lib/i18n/ko.json`에서 `"newsHook"` 블록을:
```json
    "newsHook": {
      "kicker": "속보",
      "body": "인류가 현존 최강 AI를 다시 넘어섰습니다. 신진서 9단이 2점 접바둑 3번기에서 카타고를 2승 1패로 꺾었죠. 그 카타고(Human-SL)가 지금 잉크바둑에서 당신을 기다립니다.",
      "guide": "닉네임만 입력하면 바로 그 AI와 한 판이 시작됩니다."
    },
```
다음으로 교체:
```json
    "newsHook": {
      "kicker": "속보"
    },
```

`web/lib/i18n/en.json`에서 동일하게:
```json
    "newsHook": {
      "kicker": "Breaking",
      "body": "Humanity just edged the strongest AI alive — 9-dan Shin Jinseo beat KataGo 2–1 in a three-game match at a two-stone handicap. That same KataGo (Human-SL) is waiting for you on Inkbaduk.",
      "guide": "Enter a nickname and take on that very AI."
    },
```
다음으로 교체:
```json
    "newsHook": {
      "kicker": "Breaking"
    },
```

- [ ] **Step 4: i18n 키 동등성 테스트 + 타입체크 + 빌드 확인**

Run:
```bash
cd web
npm test -- --run tests/i18n.test.ts
npm run type-check
npm run build
```
Expected: 셋 다 통과. `npm run build`가 실패하면 `_HomeLanding.tsx`의 prop 배선을 다시 확인한다.

- [ ] **Step 5: 홈 전체 테스트 스위트 통과 확인**

Run: `cd web && npm test -- --run`
Expected: 전부 통과 (신규 4개 포함)

- [ ] **Step 6: 커밋**

```bash
git add web/app/page.tsx web/app/_HomeLanding.tsx web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "feat(web): 홈 랜딩에 news-hook.json 데이터 배선, 구 i18n 문구 제거"
```

---

### Task 4: 파이프라인 프롬프트 문서 (`news-hook-prompt.md`)

**Files:**
- Create: `docs/ops/news-hook-prompt.md`

**Interfaces:**
- Consumes: 없음(헤드리스 Claude가 직접 읽는 절차 문서)
- Produces: `ops/report-job-status.sh news-hook <ok|warn|fail> "<summary>"` 호출 계약(Task 5가 스크립트에서 이 프롬프트를 `claude -p`에 전달)

- [ ] **Step 1: 프롬프트 문서 작성**

`docs/ops/news-hook-prompt.md`:
```markdown
# 주간 속보 훅 갱신 사이클

너는 inkbaduk의 속보 훅 갱신 세션이다. launchd가 매주 일요일 05:00에 1회 깨운 것이다.
작업 디렉터리는 리포 루트(`/Users/daegong/projects/baduk`)다.

## 시작 전 필수

1. `web/content/news-hook.json`을 읽어 현재 게시된 `source_url`을 확인한다(같은 사건 재게시 방지용).
2. 이 사이클의 대상 도메인은 **바둑·프로기사·AI-vs-인간 대국 관련 뉴스로 한정**한다. 그 외 화제(일반 AI 산업 뉴스 등)는 대상이 아니다.

## 1회 실행

1. **뉴스 탐색** — WebSearch 도구로 최근 7일 이내 "바둑 프로기사 AI 대국" 계열 키워드로 검색한다.

2. **판정(게이트)** — 검색 결과 중 아래 세 조건을 **모두** 만족하는 항목이 있는지 스스로 평가한다.
   - 검증 가능한 출처 URL이 있다(대형 언론·바둑 매체·공식 발표).
   - 바둑·프로기사·AI-vs-인간 대국 범위 안이다.
   - 그 URL이 현재 `news-hook.json`의 `source_url`과 다르다(같은 사건 재탕 아님).

   만족하는 항목이 **없으면** — 아무 파일도 바꾸지 않고 바로 6단계(로그·기록)로 간다. 이 도메인 뉴스는 몇 주~몇 달에 한 번만 나올 수 있으므로, "이번 주는 변경 없음"이 정상 결과다. **소재가 마땅치 않다고 억지로 만들어내지 않는다.**

3. **문구 생성** — 발견한 사실을 한국어·영어 마케팅 톤으로 각각 직접 서술한다(기존 `web/content/news-hook.json`의 `body_ko`/`guide_ko` 문체를 참고). 기사 원문을 인용하지 않고 사실만 자기 문장으로 재구성한다. 다음 필드를 채운 JSON 초안을 메모리에 준비한다: `updated_at`(오늘 날짜, `YYYY-MM-DD`), `source_url`, `body_ko`, `body_en`, `guide_ko`, `guide_en`.

4. **사실검증** — `Agent` 도구로 별도 서브에이전트를 호출해 다음을 지시한다:
   "다음 URL의 실제 내용을 읽고, 아래 한국어 문장이 그 내용과 사실적으로 일치하는지만 판정해줘(언어 자연스러움은 보지 마). URL: <source_url> / 문장: <body_ko> — '일치' 또는 '불일치: <이유>'로만 답해."
   응답이 "불일치"로 시작하면 게시하지 않고 사유를 로그에 남긴 뒤 6단계로 간다.

5. **게시** — 4단계를 통과하면:
   - `web/content/news-hook.json`을 3단계에서 준비한 JSON으로 덮어쓴다.
   - `git add web/content/news-hook.json`
   - `git commit -m "content(news-hook): <한 줄 요약>"`
   - `git push origin main` — 거부되면(non-fast-forward) `git pull --rebase origin main` 후 1회만 재시도. 그래도 실패하면 push는 보류하고 로그에 기록한다(커밋은 로컬에 남고 prod 작업트리에 이미 반영되므로 라이브에는 노출됨).
   - 재빌드·재기동은 불필요하다 — 홈 서버 컴포넌트가 매 요청 시 이 파일을 읽는다.

6. **로그·기록**
   - `ops/report-job-status.sh news-hook ok "<요약>"` — 게시했으면 "<한 줄 사건 요약> 게시", 변경 없으면 "이번 주 대상 뉴스 없음", 사실검증 실패면 "사실검증 불일치로 게시 보류: <사유>".
   - `state/log/YYYY-MM-DD.md`에 한 줄 추가(없으면 생성).

## 끝낼 때

한 일을 2~3줄로 요약하고 종료. 이 세션은 1회성이다.
```

- [ ] **Step 2: 문서 리뷰 — Global Constraints와 대조**

Task 4는 코드가 아니므로 자동 테스트가 없다. 대신 이 스텝에서 방금 쓴 프롬프트 문서를 다시 읽고, 이 플랜의 Global Constraints(원문 인용 금지·출처 URL 필수·뉴스 없으면 유지·도메인 범위 한정) 네 가지가 프롬프트 본문에 각각 명시돼 있는지 체크리스트로 확인한다. 빠진 게 있으면 이 스텝에서 바로 추가한다.

- [ ] **Step 3: 커밋**

```bash
git add docs/ops/news-hook-prompt.md
git commit -m "docs(ops): 주간 속보 훅 갱신 사이클 프롬프트 추가"
```

---

### Task 5: launchd 실행 스크립트

**Files:**
- Create: `ops/run-news-hook.sh`

**Interfaces:**
- Consumes: `docs/ops/news-hook-prompt.md` (Task 4)
- Produces: `docs/ops/state/log/news-hook-runs.log` 성공/실패 마커(`news-hook 시작`/`news-hook 종료`/`비정상 종료`) — Task 6의 `check-staleness.sh` JOBS 항목이 이 마커 문자열을 그대로 참조한다.

- [ ] **Step 1: 스크립트 작성** (기존 `ops/run-content-draft.sh`와 동일 구조)

`ops/run-news-hook.sh`:
```bash
#!/usr/bin/env bash
# launchd가 매주 일요일 05:00 호출 — 속보 훅 갱신 헤드리스 Claude를 1회 실행.
set -euo pipefail
# launchd는 로그인 셸 PATH를 상속하지 않는다 — Homebrew 경로(gh·claude 등)를 명시적으로 앞에 붙인다.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"

[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }

mkdir -p docs/ops/state/log
RUNLOG="docs/ops/state/log/news-hook-runs.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] news-hook 시작" >> "$RUNLOG"

/opt/homebrew/bin/claude -p "$(cat docs/ops/news-hook-prompt.md)" \
  --dangerously-skip-permissions \
  --channels plugin:telegram@claude-plugins-official \
  >> "$RUNLOG" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] news-hook 종료" >> "$RUNLOG"
```

- [ ] **Step 2: 실행 권한 부여**

Run: `chmod +x ops/run-news-hook.sh`

- [ ] **Step 3: 문법 검증**

Run: `bash -n ops/run-news-hook.sh`
Expected: 출력 없음(문법 오류 없음)

- [ ] **Step 4: 커밋**

```bash
git add ops/run-news-hook.sh
git commit -m "chore(ops): news-hook 실행 스크립트 추가"
```

---

### Task 6: launchd 등록 + watchdog·오케스트레이터 통합

**Files:**
- Create: `ops/launchd/com.inkbaduk.news-hook.plist`
- Modify: `ops/check-staleness.sh`
- Modify: `docs/ops/orchestrator-prompt.md`

**Interfaces:**
- Consumes: `ops/run-news-hook.sh` (Task 5), `docs/ops/state/log/news-hook-runs.log` 마커 문자열(Task 5)

- [ ] **Step 1: plist 작성** (기존 `content-ingest`·`analytics-weekly`와 같은 일요일 슬롯 패턴, 시각만 비움)

`ops/launchd/com.inkbaduk.news-hook.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- 매주 일요일 05:00 속보 훅 갱신을 실행하는 launchd 작업 (주 1회). -->
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.inkbaduk.news-hook</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/daegong/projects/baduk/ops/run-news-hook.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>0</integer>
    <key>Hour</key><integer>5</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/news-hook.out.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/news-hook.err.log</string>
</dict>
</plist>
```
(일요일 05:00은 기존 `content-ingest` 03:00, `analytics-weekly` 09:00 사이의 빈 슬롯 — `launchctl list | grep inkbaduk` 및 `for f in ~/Library/LaunchAgents/com.inkbaduk.*.plist; do grep -A2 Hour "$f"; done`로 최종 충돌 여부를 이 스텝에서 재확인한다.)

- [ ] **Step 2: `check-staleness.sh`의 JOBS 배열에 추가**

`ops/check-staleness.sh`에서 아래 줄(analytics-weekly 항목 바로 아래)을 찾는다:
```bash
  "analytics-weekly|analytics-weekly-runs.log|691200|analytics-weekly 종료"  # 8d
```
바로 아래에 추가:
```bash
  "news-hook|news-hook-runs.log|691200|news-hook 종료"  # 8d (plist 주 1회 일 05:00, 7d 주기 + 1d 마진)
```

- [ ] **Step 3: 오케스트레이터 다이제스트 집계 대상에 추가**

`docs/ops/orchestrator-prompt.md`에서 다음 문장을 찾는다:
```
     이 행은 `state/jobs/*.json`을 쓰는 세 잡(`dev-cycle`·`content-draft`·`analytics-weekly`)만
```
다음으로 교체:
```
     이 행은 `state/jobs/*.json`을 쓰는 네 잡(`dev-cycle`·`content-draft`·`analytics-weekly`·`news-hook`)만
```

- [ ] **Step 4: 문법·충돌 검증**

Run:
```bash
plutil -lint ops/launchd/com.inkbaduk.news-hook.plist
bash -n ops/check-staleness.sh
for f in ~/Library/LaunchAgents/com.inkbaduk.*.plist; do echo "=== $(basename "$f") ==="; grep -A2 "Weekday\|^\s*<key>Hour" "$f"; done
```
Expected: `plutil`이 "OK" 출력, `bash -n` 무출력, 시각 목록에 일요일 05:00이 다른 어떤 job과도 겹치지 않음.

- [ ] **Step 5: 커밋**

```bash
git add ops/launchd/com.inkbaduk.news-hook.plist ops/check-staleness.sh docs/ops/orchestrator-prompt.md
git commit -m "chore(ops): news-hook launchd 등록 + watchdog·오케스트레이터 통합"
```

---

### Task 7: 드라이런 검증 + 실활성화 (승인 게이트)

이 태스크는 **실제 prod main에 자동 커밋·push하는 상시 자동화를 처음 켜는 단계**라 마지막에 별도로 사람 확인을 받는다. Task 1-6까지는 코드·설정 작성일 뿐 아직 아무것도 자동 실행되지 않는다.

**Files:** 없음(실행·확인만)

- [ ] **Step 1: 수동 드라이런 — 스크립트가 끝까지 정상 완주하는지 확인**

Run: `bash ops/run-news-hook.sh`

Expected: `docs/ops/state/log/news-hook-runs.log`에 "news-hook 시작"과 "news-hook 종료"가 정상 순서로 기록되고 그 사이에 "비정상 종료"가 없다. `docs/ops/state/jobs/news-hook.json`이 생성되고 `status`가 `ok`다. 이번 주 실제로 반영 조건을 만족하는 뉴스가 없다면 `web/content/news-hook.json`은 **변경되지 않아야 한다** — `git status`로 확인한다.

- [ ] **Step 2: 결과에 따라 분기**

- 게시가 실제로 일어났다면(`web/content/news-hook.json`이 바뀌었다면): `git log -1 -p web/content/news-hook.json`으로 diff를 직접 읽고, `source_url`을 브라우저로 열어 `body_ko`의 사실 주장이 실제로 맞는지 사람이 한 번 더 확인한다. 문제 없으면 그대로 두고(이미 push됨), 문제가 있으면 즉시 `git revert`한다.
- 변경이 없었다면: 정상. 로그의 사유("이번 주 대상 뉴스 없음" 등)만 확인한다.

- [ ] **Step 3: launchd 등록 (사람 승인 후 실행)**

```bash
bash ops/sync-launchd.sh --check   # MISSING com.inkbaduk.news-hook.plist 확인
bash ops/sync-launchd.sh           # 실제 설치 + bootstrap
launchctl list | grep inkbaduk.news-hook   # 등록 확인
```

- [ ] **Step 4: 최종 보고**

`docs/ops/state/log/YYYY-MM-DD.md`(오늘 날짜)에 news-hook job 신설·최초 드라이런 결과·launchd 등록 완료를 한 줄로 기록한다.

## Self-Review 기록

- **스펙 커버리지**: 스펙의 5단계 파이프라인(탐색/게이트/생성/사실검증/게시) → Task 4 프롬프트에 1:1 대응. 렌더링 전환(정적→동적) → Task 1-3. 운영 통합(스크립트·plist·watchdog·오케스트레이터) → Task 5-6. 기술 리스크(WebSearch 헤드리스 가용성) → 플랜 작성 전 스파이크로 이미 해소, Global Constraints에 기록. 성공 기준 3가지(재빌드 불필요/사실검증 게이트 검증/관찰 후 등급 조정) → Task 1-3(재빌드 불필요는 Task 3 Step 4의 build 확인으로 실증), Task 4 Step 4의 사실검증 로직, Task 7 Step 2의 관찰 절차로 커버.
- **플레이스홀더 스캔**: "TBD"·"나중에"·"적절히 처리" 패턴 없음. Task 4는 코드가 아니라 자동 테스트가 없다는 점을 명시했고, 대신 체크리스트 방식의 자가검증 스텝을 넣었다.
- **타입 일관성**: `NewsHookData`(Task 1에서 정의) 필드명(`updated_at`/`source_url`/`body_ko`/`body_en`/`guide_ko`/`guide_en`)이 Task 2 컴포넌트, Task 3 프롬프트 문서의 게시 절차, Task 1 시드 JSON에서 모두 동일하게 쓰임을 확인함.

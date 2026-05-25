# Glossary 미디어 통합 — Phase 1 (정적 이미지 + 보드 다이어그램)

- 작성일: 2026-05-26
- 상태: 설계 승인 완료, 구현 계획 대기
- 범위: 글로서리 마크다운 콘텐츠에 보드 다이어그램·정적 이미지를 첫 단계로 추가. 동영상은 Phase 2 별도 spec.
- 선행: [`2026-05-25-glossary-faq-redesign-design.md`](2026-05-25-glossary-faq-redesign-design.md)

## 배경

PR #37로 글로서리·FAQ가 Editorial Hardcover 디자인을 갖췄지만 콘텐츠는 1100자 내외 순수 텍스트. 바둑 개념(축·빅·단/급)은 본질적으로 보드 위 위치라 텍스트만으로는 학습 효과가 약하다. 시각 자료를 더해 "이미지/동영상 포함 설명"으로 격상한다.

## 결정된 접근 — 하이브리드 (도메인 다이어그램 + 일반 이미지), Phase 1만

검토한 3안 (도메인 다이어그램 중심 / 일반 이미지·영상 / 하이브리드) 중 **하이브리드** 채택 후 scope을 Phase 1으로 좁힘:

- **Phase 1 (이번 spec)**: 보드 다이어그램 + 정적 이미지(SVG/PNG)
- **Phase 2 (별도 spec)**: 동영상 (YouTube embed·MP4·GIF 중 추후 결정)

Phase 분할 이유:
- 동영상은 호스팅·encoding·플레이어 UX·저작권 검토가 별도 비용. 1차 머지·검증 후 결정이 안전.
- 보드 다이어그램만으로도 도메인 학습 효과 큼 (축·빅 같은 개념은 위치가 본질).
- 단일 PR 관리·검증 용이.

## 목표 / 비목표

### 목표
1. 마크다운 본문에서 보드 다이어그램을 코드블록 한 곳에 정의해 정적 SVG로 렌더
2. 마크다운 표준 이미지(`![]()`)를 figure/figcaption 패턴으로 렌더, Editorial 토큰 적용
3. 3개 글로서리(bik·dan-gup·chuk)에 다이어그램·이미지 실제 적용
4. 마크다운 author 친화 (외부 도구 없이 위치 문자열 + 캡션만으로 다이어그램 생성)

### 비목표 (YAGNI)
- 동영상 (Phase 2)
- 인터랙티브 시퀀스 재생 (다음 단계 보기 등)
- next/image (도메인 설정 부담, raw `<img>` 충분)
- LLM 자동 다이어그램 생성 (content-draft 확장)
- 다국어 콘텐츠 자체 (UI i18n은 유지)
- 코드 syntax highlighting
- 마크다운 안 React 컴포넌트 인라인 일반화 (MDX 전환)
- Board.tsx 인터랙티브 컴포넌트와의 코드 통합(시각 토큰만 공유)

## 설계

### 섹션 1 — 마크다운 보드 다이어그램 (커스텀 fenced code block)

저자가 마크다운 본문에 ``` ```board ``` 코드블록을 쓰면 정적 SVG 다이어그램으로 변환.

**소스 형식** (YAML 부분집합, 직접 파서):

````
```board
size: 9
position: |
  .........
  .........
  ....B....
  ...WB....
  ....W....
  .........
  .........
  .........
  .........
caption: 축의 시작 — 흑이 백을 한 칸씩 추격해 활로를 좁힌다.
```
````

필드:
- `size`: 9 / 13 / 19 (정수)
- `position`: 멀티라인 문자열, 각 행 size 문자 (`.` 빈 칸, `B` 흑, `W` 백). 행 수 = size.
- `caption`: figcaption에 표시 (선택)

**변환 결과 HTML**:
```html
<figure class="board-diagram">
  <svg viewBox="0 0 480 480" role="img" aria-label="{caption or 'Board diagram'}">
    <!-- grid, star points, stones -->
  </svg>
  <figcaption>{caption}</figcaption>
</figure>
```

**파싱 규칙**:
- size 누락 → 19 기본
- position 행 수 size와 다르면 → 모자라면 빈 행 padding, 넘치면 잘라냄. 콘솔 경고.
- 행 길이가 size와 다르면 → padding/자르기 + 경고.
- caption 누락 → figcaption 자체 생략.
- 잘못된 문자 (`B`·`W`·`.` 외) → `.` 취급 + 경고.

자체 mini YAML 파서 (gray-matter는 frontmatter 전용). 50줄 정도.

### 섹션 2 — 마크다운 표준 이미지 → figure 변환

```markdown
![빅의 일반적 형태](/content/glossary/bik/figure-2.svg)
```

marked의 `renderer.image` 옵션 override:

```html
<figure class="content-image">
  <img src="/content/glossary/bik/figure-2.svg" alt="빅의 일반적 형태" loading="lazy" />
  <figcaption>빅의 일반적 형태</figcaption>
</figure>
```

- alt 텍스트가 figcaption 동시 사용 (SEO + 시각).
- `loading="lazy"`로 below-the-fold 이미지 지연 로드.
- next/image 미사용 — `<img>`로 충분. SVG는 어차피 작고, 외부 도메인 불필요.

### 섹션 3 — `lib/board-svg.ts` 신규

순수 함수 (server-side 호출 가능, no React):

```ts
export interface BoardSpec {
  size: number;
  position: string[]; // 행별 size 문자
  caption?: string;
}

export function parseBoardCodeBlock(source: string): BoardSpec;
export function boardToSvg(spec: BoardSpec): string; // <svg> markup
export function boardCodeBlockToHtml(source: string): string; // <figure>...</figure>
```

**SVG 사양** (Board.tsx 토큰과 시각 일치):
- viewBox `0 0 480 480` (반응형 + 모바일 대응)
- 격자: hairline `stroke="rgb(var(--ink-mute))"` (CSS 변수 활용)
- 화점: 같은 색 작은 원
- 흑돌: `fill="rgb(var(--ink))"` + 미세 그라데이션 없음 (정적 평면)
- 백돌: `fill="rgb(var(--paper))"` + `stroke="rgb(var(--ink-mute))"`
- 좌표축 라벨 없음 (단순)
- 별도 lib — Board.tsx의 use client·interactive 로직과 분리, 토큰만 공유

### 섹션 4 — `lib/content.ts` 보강

```ts
import { marked } from "marked";
import { boardCodeBlockToHtml } from "./board-svg";

const renderer = new marked.Renderer();
renderer.code = (code, infostring) => {
  if (infostring?.trim() === "board") {
    return boardCodeBlockToHtml(code);
  }
  return `<pre><code>${escapeHtml(code)}</code></pre>`;
};
renderer.image = (href, title, text) => {
  const alt = escapeHtml(text || "");
  return `<figure class="content-image"><img src="${escapeHtml(href || "")}" alt="${alt}" loading="lazy" />${
    alt ? `<figcaption>${alt}</figcaption>` : ""
  }</figure>`;
};
marked.use({ renderer });
```

`extractExcerpt` 보강: ``` ```board ``` 코드블록 + 이미지 마크다운(`![...](...)`)을 추출 전 제거. 이미 markdown header·list·bold·code 제거하는 정규식 체인에 추가.

### 섹션 5 — `editorial-prose` 스타일 보강 (globals.css)

기존 `@layer components` 안에 추가:

```css
.editorial-prose figure {
  @apply my-8 flex flex-col items-center gap-3;
}
.editorial-prose figure img {
  @apply max-w-full border border-ink-faint bg-paper;
}
.editorial-prose figure figcaption {
  @apply font-mono text-xs uppercase tracking-label text-ink-mute text-center;
}
.editorial-prose .board-diagram svg {
  @apply w-full max-w-[480px] border border-ink-faint bg-paper-deep;
}
```

(figure 공통 스타일 + board-diagram 특수만 — content-image 클래스는 figure 공통으로 충분.)

### 섹션 6 — 콘텐츠 업데이트 (3 항목)

**`web/content/glossary/chuk.md`** — 다이어그램 2개:
- Fig 1: 축의 시작 — 흑이 백을 단수하며 추격 (9×9 보드, 5수 정도)
- Fig 2: 축머리가 있어 축이 무효 — 멀리 백 돌이 추격 경로 위에 놓여 활로 회복 (9×9)
- 본문 흐름에 자연스럽게 삽입 (예: 1단락 끝, 2단락 끝)

**`web/content/glossary/bik.md`** — 다이어그램 1 + 이미지 1:
- Fig 1: 빅의 전형적 형태 (9×9, 양쪽 돌이 얽혀 양보 불가 위치)
- Image: 외부 이미지 1개 (또는 모두 다이어그램). 단순화 위해 다이어그램만 1개.

**`web/content/glossary/dan-gup.md`** — 정적 SVG 1개:
- Rank ladder SVG (직접 그린, 1단~9단·18급~1급 단계표). `web/public/content/glossary/dan-gup/rank-ladder.svg`
- 마크다운에서 `![단·급 체계 도식](/content/glossary/dan-gup/rank-ladder.svg)` 참조

### 섹션 7 — 자산 디렉터리

```
web/public/content/glossary/
  bik/         (Phase 1에서 비어있음 — 다이어그램만)
  chuk/        (Phase 1에서 비어있음 — 다이어그램만)
  dan-gup/
    rank-ladder.svg
```

`web/public/content/`는 신규. 마크다운에서 절대 경로(`/content/glossary/...`)로 참조.

## 컴포넌트 / 파일 매트릭스

| 파일 | 종류 | 책임 |
|---|---|---|
| `web/lib/board-svg.ts` | 신규 | parseBoardCodeBlock + boardToSvg + boardCodeBlockToHtml |
| `web/lib/content.ts` | 수정 | marked renderer 보드/이미지 override, extractExcerpt 보강 |
| `web/app/globals.css` | 수정 | `.editorial-prose figure/img/.board-diagram` 토큰 |
| `web/public/content/glossary/dan-gup/rank-ladder.svg` | 신규 | 단·급 단계표 SVG (직접 작성) |
| `web/content/glossary/chuk.md` | 수정 | board 코드블록 2개 삽입 |
| `web/content/glossary/bik.md` | 수정 | board 코드블록 1개 삽입 |
| `web/content/glossary/dan-gup.md` | 수정 | 이미지 마크다운 1개 삽입 |
| `web/tests/board-svg.test.ts` | 신규 | parseBoardCodeBlock·boardToSvg 단위 테스트 |
| `web/tests/content.media.test.ts` | 신규 | marked renderer board/image override + extractExcerpt 미디어 무시 |

## 데이터 흐름

```
content/glossary/<slug>.md
       │
       ├── frontmatter (matter)
       └── body markdown
              │
              ├── ```board ... ```        → renderer.code → boardCodeBlockToHtml → <figure><svg/><figcaption/></figure>
              ├── ![alt](path)            → renderer.image → <figure><img/><figcaption/></figure>
              └── 기타 markdown          → marked 기본 변환
                          │
                          ▼
                   html string → editorial-prose CSS 토큰 매핑 → 렌더
```

excerpt도 board 코드블록 + 이미지 마크다운을 사전에 제거한 본문에서 추출.

## 테스트

**`board-svg.test.ts`** (단위, vitest):
- `parseBoardCodeBlock("size: 9\nposition: |\n  .B.\n  ...\n  ...\ncaption: x")` → spec 객체 정확
- size 누락 → 19 기본
- position 행 수 mismatch → 경고 + 보정
- 잘못 문자 → `.` 치환
- `boardToSvg({size: 9, position: [".........", ...]})` → SVG에 `<svg`, 격자 path/line, 화점 수, 돌 좌표 검증

**`content.media.test.ts`**:
- ``` ```board ``` 코드블록 입력 → html에 `<figure class="board-diagram">` 포함
- `![alt](path)` 입력 → html에 `<figure class="content-image">` + `<figcaption>alt</figcaption>` 포함
- `extractExcerpt`가 board 코드블록 + 이미지 마크다운 무시한 텍스트 본문에서 추출 확인
- 일반 fenced code block (` ```ts `)은 기본 `<pre><code>`로 폴백 확인

기존 vitest 회귀 — 전체 PASS.

## 자율성 등급

| 작업 | 등급 |
|---|---|
| 코드·CSS·테스트 (worktree) | 🟢 자율 |
| 콘텐츠 마크다운 수정 | 🟢 자율 |
| 신규 SVG 자산 (rank-ladder.svg) | 🟢 자율 |
| PR 생성 + 머지 | 🟡 사람 승인 (기존 패턴) |
| build + web kickstart | 🟡 (PR 머지와 묶어 승인) |

## 위험 / 미해결

1. **Board.tsx와 board-svg.ts 시각 일관성** — 토큰을 공유하지만 SVG는 hover/theme 변화 없음. 정적 다이어그램이므로 light/dark 모두 작동하는 토큰만 사용. 첫 페인트가 의도된 시각.
2. **position 파싱 에러** — fallback (자르기/padding + 경고). 빌드 깨지지 않게 보수적.
3. **SVG 모바일 폭** — `w-full max-w-[480px]`로 100%/480px 캡. 좁은 화면에서 글자 가독성 코너 케이스는 후속.
4. **figcaption=alt 단순화** — 마크다운 alt 텍스트를 figcaption으로 그대로 사용. 별도 figcaption 필드는 미지원 (단순). 더 풍부한 caption이 필요하면 후속 spec에서 frontmatter 확장.
5. **외부 이미지 도메인 미지원** — 외부 URL 이미지는 작동하지만 next/image 안 쓰므로 최적화 없음. 일단 모든 자산을 `public/`에 내부 호스팅.
6. **rank-ladder.svg 미적 품질** — 자체 작성 SVG라 디자인 손이 많이 갈 수 있음. 1차는 단순 사다리 + 텍스트 라벨로 충분 (Editorial 톤 일치하면 OK).

## 단계 분해 (writing-plans에서 상세)

1. `lib/board-svg.ts` `parseBoardCodeBlock` + 단위 테스트
2. `lib/board-svg.ts` `boardToSvg` + 단위 테스트
3. `lib/board-svg.ts` `boardCodeBlockToHtml` (1+2 wrap)
4. `lib/content.ts` marked renderer.code override (board) + 테스트
5. `lib/content.ts` marked renderer.image override (figure) + 테스트
6. `lib/content.ts::extractExcerpt` 보강 (board/image 제거) + 회귀
7. `globals.css` `.editorial-prose figure / img / .board-diagram` 토큰
8. `public/content/glossary/dan-gup/rank-ladder.svg` 직접 작성
9. `content/glossary/chuk.md` 다이어그램 2개 삽입
10. `content/glossary/bik.md` 다이어그램 1개 삽입
11. `content/glossary/dan-gup.md` 이미지 마크다운 1개 삽입
12. 전체 type-check + lint + vitest + build → PR + 🟡 머지 + 라이브

총 12 task, 단일 PR.

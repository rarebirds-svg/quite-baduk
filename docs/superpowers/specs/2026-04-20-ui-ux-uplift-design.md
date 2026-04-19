# UI/UX 업리프트 — 공개 서비스 수준의 디자인 시스템 구축

- **작성일**: 2026-04-20
- **상태**: 설계 승인 대기
- **범위**: `web/` 전체 프론트엔드. 백엔드·KataGo·DB·API 계약은 변경하지 않음
- **선행 변경**: 없음 (기존 미커밋 작업 `web/components/Board.tsx` 반응형 스케일, `web/app/game/play/[id]/page.tsx` 돌 터치 사운드는 Phase 2에서 병합)

## 1. 목표와 배경

**목표**: 현재 기능은 완성되어 있으나 시각 디자인이 평이해 공개 서비스로 론칭하기 부족한 상태다. 디자인 시스템을 구축하고 전체 화면을 프로덕션 품질의 "Editorial Hardcover" 미학으로 재구성해 타겟 사용자(진지한 경쟁 플레이어)에게 적합한 시각·인터랙션 품질을 확보한다.

**비목표**:
- 신규 게임 기능(시간 제어, PvP, OAuth, 챗) 추가 — 이후 릴리스
- 기능 동작 변경 — 본 업리프트는 "외형 + UX 폴리시" 전용
- 백엔드·API·WS 스키마 변경
- 모바일 전용 앱 개발

**성공 기준**:
- 9개 현존 화면 + 404/에러 바운더리가 공통 시스템 토큰·타이포·컴포넌트로 렌더링됨
- 라이트(Day)·다크(Night) 두 모드 모두 폴리시드 — SSR 플래시 없음
- Vitest·Playwright 기존 테스트 모두 통과 + 주요 화면 시각 스크린샷 추가
- Lighthouse 데스크톱 Performance ≥ 90, Accessibility ≥ 95
- 키보드만으로 대국 흐름(로그인 → 새 게임 → 착수 → 패스/기권) 완수 가능

## 2. 디자인 컨셉

### 2.1 방향: Editorial Hardcover (Journal)

FT·양장본 저널 스타일의 "조용한 권위." 세리프 본문 + 얇은 규칙선 + 크림지 배경 + 옥스블러드 악센트. 장식 애니메이션·그림자 없음, 타이포·여백·규칙선으로 위계 구축. 타겟은 바둑 1급~유단자 수준의 경쟁 플레이어로, 기보를 "기록물"로 대한다.

### 2.2 반(反)-패턴

- AI 스타일의 보라 그라디언트, 카드 드롭섀도, 과도한 둥근 모서리(radius > 4px), Inter 기본 폰트 — 모두 **금지**
- 장식용 모션(바운스, 패럴랙스, stagger reveal) — **금지**
- 이모지 아이콘 (현재 TopNav 언어 토글이 이모지 사용 중 → 교체)

## 3. 디자인 토큰

### 3.1 컬러

**Light (Day Edition, 기본)**
| 토큰 | 값 | 용도 |
|---|---|---|
| `paper` | `#F5EFE6` | 페이지 배경, 전역 |
| `paper-deep` | `#E9DFC9` | 보드 표면, 카드 강조 배경 |
| `ink` | `#1A1715` | 본문·헤딩 텍스트, 강조 규칙선, 흑돌 |
| `ink-mute` | `#6B635A` | 보조 텍스트, 메타 |
| `ink-faint` | `#B8AFA3` | 1px 규칙선(20% 대신 이 색 사용 가능), 비활성 |
| `oxblood` | `#7B1E24` | Primary 악센트 — 브랜드, 힌트, 링크, 에러 |
| `gold` | `#A37B1E` | 승률·성취, 제한적 사용 |
| `moss` | `#2E4A3A` | 성공·최적수 |
| `stone-black` | `#0F0D0C` | 흑돌 (ink보다 약간 짙음) |
| `stone-white` | `#FAF5EC` | 백돌 |

**Dark (Night Edition)** — 시스템 설정 자동 감지(`prefers-color-scheme`) + 사용자 수동 토글로 override 가능. 기본값은 `system`.
| 토큰 | 값 | 대응 |
|---|---|---|
| `paper` | `#1C1917` | — |
| `paper-deep` | `#26221F` | — |
| `ink` | `#F2EBDF` | — |
| `ink-mute` | `#9B9288` | — |
| `ink-faint` | `#5C544D` | — |
| `oxblood` | `#C85058` | 대비 ↑ |
| `gold` | `#D9A648` | — |
| `moss` | `#6A9478` | — |
| `stone-black` | `#0F0D0C` | 불변 (규칙) |
| `stone-white` | `#FAF5EC` | 불변 (규칙) |

**의미 토큰 (semantic)** — 위 raw 토큰을 참조
- `--color-fg` → ink / ink (dark)
- `--color-fg-mute` → ink-mute
- `--color-bg` → paper
- `--color-bg-raised` → paper-deep
- `--color-border` → ink-faint @ light, ink-faint @ dark
- `--color-border-strong` → ink
- `--color-accent` → oxblood
- `--color-success` → moss
- `--color-warn` → gold
- `--color-danger` → oxblood (강조 시 bg 사용)

### 3.2 타이포그래피

**폰트 스택**
- `font-display` / `font-serif`: **Newsreader** (Google Fonts, variable, opsz 6..72) — 헤딩·영문 본문
- `font-sans`: **Pretendard Variable** (jsDelivr CDN) — 한글 본문 + UI 라벨
- `font-sans-en`: **IBM Plex Sans** (Google Fonts) — 영문 라벨·캡션 (Pretendard와 혼용 시 선택)
- `font-mono`: **IBM Plex Mono** (Google Fonts) — 숫자·좌표·단축키 힌트

**스케일**
| 명칭 | 크기/라인하이트 | 폰트 | 용도 |
|---|---|---|---|
| display-xl | 48/56 -0.02em | serif 600 | 홈 히어로 |
| display | 32/40 -0.02em | serif 600 | 페이지 타이틀 |
| h1 | 24/32 -0.015em | serif 600 | 섹션 |
| h2 | 20/28 -0.01em | serif 600 | 서브섹션 |
| h3 | 16/24 | serif 600 | 카드 제목 |
| body | 14/22 | sans 400 | 본문 |
| small | 12/18 | sans 400 | 메타 |
| label | 11/14 0.16em UPPER | sans 600 | 라벨·섹션 마커 |
| data-xl | 32/36 -0.02em tabular | mono 500 | 승률 등 주요 숫자 |
| data | 20/24 tabular | mono 500 | 시간·포인트 |
| data-sm | 13/18 tabular | mono 500 | 좌표·목록 |

모든 숫자는 `font-variant-numeric: tabular-nums` 적용. 한국어 혼용 시 Pretendard 기본.

### 3.3 간격·radius·그림자·모션

- **간격 스케일**: `space-1` 4px → `space-16` 64px (Tailwind 기본 4/8/12/16/24/32/48/64 유지)
- **radius**: `0` (카드·보드), `2px` (버튼·입력 기본), `9999` (토글·배지·스톤)
- **그림자**: 없음. 위계는 규칙선과 배경 대비로 표현
- **규칙선**: `border-width: 1px`, 기본 `border-ink-faint`, 강조 `border-ink`
- **모션**:
  - `transition-base`: 150ms ease-out (색·배경·테두리)
  - `transition-stone`: 300ms cubic-bezier(.2,.7,.2,1) (돌 착수 스케일·그림자 인)
  - `transition-page`: 200ms ease-out (라우트 전환)
  - 장식적 엔트리 애니메이션·stagger 없음

### 3.4 아이콘

- **Lucide React** (`lucide-react`), 크기 16px 기본, `strokeWidth={1.5}`
- 이모지 아이콘 모두 제거 (TopNav 언어 토글 등)
- 바둑 특화 기호(패스·기권·핸디캡)는 `components/editorial/icons/`에 독자 SVG

## 4. 기술 아키텍처

### 4.1 디렉터리 구조 변경

```
web/
├── app/
│   ├── globals.css              # 토큰 CSS 변수 · Tailwind layer · 폰트 변수
│   ├── layout.tsx               # ThemeProvider(next-themes) + Sonner Toaster + fonts
│   └── (screens)                # Phase 2-3에서 재구성
├── components/
│   ├── ui/                      # shadcn 복붙 (10종, §4.3)
│   └── editorial/               # 독자 프리미티브 (§4.4)
├── lib/
│   ├── tokens.ts                # TS 상수 export (색·간격·모션)
│   ├── fonts.ts                 # next/font/google 설정
│   ├── cn.ts                    # clsx + tailwind-merge
│   └── (기존 i18n·api·ws·board·theme·sgf·soundfx 유지)
└── tailwind.config.ts           # 토큰을 theme.extend에 매핑
```

### 4.2 의존성 추가

```jsonc
// web/package.json 추가 — 버전은 설치 시점의 latest stable 고정 (Phase 1 PR에서 확정)
"dependencies": {
  "@radix-ui/react-dialog": "^1",
  "@radix-ui/react-dropdown-menu": "^2",
  "@radix-ui/react-label": "^2",
  "@radix-ui/react-select": "^2",
  "@radix-ui/react-separator": "^1",
  "@radix-ui/react-slot": "^1",
  "@radix-ui/react-tabs": "^1",
  "@radix-ui/react-toggle-group": "^1",
  "@radix-ui/react-tooltip": "^1",
  "class-variance-authority": "^0.7",
  "clsx": "^2",
  "tailwind-merge": "^2",
  "lucide-react": "^0.450",
  "next-themes": "^0.3",
  "sonner": "^1"
}
```

framer-motion은 도입하지 않는다 — 편집 미학과 충돌하고 CSS/Tailwind transition으로 충분.
`tailwindcss-animate`도 도입하지 않는다 — Radix primitives의 `data-state` 애니메이션은 커스텀 keyframes 몇 개로 직접 정의한다 (Phase 1 `globals.css`에서).

### 4.3 shadcn/ui 컴포넌트 카탈로그 (12종)

`components/ui/`에 **복붙(source-available)** 방식으로 설치 — CLI 대신 수동 복사 후 Editorial 토큰으로 재스타일링:

- `button.tsx` — variants: `default`(ink bg) · `outline`(ink border) · `ghost` · `link`(oxblood) · `destructive`; sizes: `sm`/`md`/`lg`/`icon`. Radius 2px. 포커스 링 ink 2px.
- `card.tsx` — bg paper-deep, border ink-faint, radius 0.
- `dialog.tsx` — Radix Dialog 기반. 배경 paper, 헤더 규칙선, 배경 오버레이 ink @ 50%.
- `dropdown-menu.tsx` — Radix. 아이템 radius 0, 호버 paper-deep.
- `input.tsx` — radius 2px, border ink-faint, 포커스 ink. 플레이스홀더 ink-mute.
- `label.tsx` — label 토큰 스타일.
- `select.tsx` — Radix Select. 트리거는 input 동일 스타일.
- `sheet.tsx` — Radix Dialog 기반 (side variant). 모바일 Play 화면 데이터 패널 슬라이드용. 배경 paper, 좌/우 규칙선.
- `tabs.tsx` — 하단 규칙선 + 활성 탭에 ink 2px 하단 라인.
- `toggle-group.tsx` — Radix ToggleGroup. Settings 테마 토글(Day/Night/System) 용. 활성 아이템 ink bg.
- `tooltip.tsx` — ink bg, paper fg, 작은 모노 텍스트.
- `separator.tsx` — `<RuleDivider>`로 래핑.
- 토스트는 `sonner` 패키지 단독 사용, shadcn toast 컴포넌트 아님.

### 4.4 editorial/ 독자 프리미티브

- `<BrandMark size?/>` — SVG: 수평 가로선과 교차하는 검정 돌, 주변 여백. 4가지 크기(16/20/24/32).
- `<Hero title subtitle? volume?/>` — display 크기 제목 + subtitle + 옵션 "Vol. I" 라벨 + 하단 규칙선.
- `<RuleDivider weight="faint"|"strong" label?/>` — 규칙선 (label 있으면 중앙에 uppercase 라벨).
- `<StatFigure value unit? label trend?/>` — 큰 숫자 + 작은 단위 + uppercase 라벨. 옵션 상승/하락 기호.
- `<DataBlock label value description?/>` — label + mono 값 + optional desc.
- `<PlayerCaption name rank color subtitle?/>` — 스톤 원 지시자 + 이름 + 랭크 + 부제.
- `<KeybindHint keys description?/>` — `<kbd>` 스타일(ink border, mono, 10px).
- `<EmptyState icon title description action?/>` — 아이콘 + 에디토리얼 카피 + 선택 CTA.
- `<Spinner size?/>` — 얇은 linear indeterminate (oxblood), Tailwind `animate-[...]`.
- `<icons/>` — pass/resign/undo/hint/handicap/pass-final 독자 SVG.

모든 프리미티브는 `cn()` 유틸로 className override 가능.

### 4.5 테마·폰트 부트스트랩

- **`next-themes`** `ThemeProvider` in `app/layout.tsx` with `attribute="class"`, `defaultTheme="system"`, `disableTransitionOnChange`.
- **next/font/google**: `Newsreader`, `IBM_Plex_Sans`, `IBM_Plex_Mono` → CSS 변수 `--font-serif/--font-sans-en/--font-mono` 주입, `<html>`에 바인딩.
- **Pretendard**: `<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">` `app/layout.tsx` `<head>`에. `--font-sans: 'Pretendard Variable', var(--font-sans-en), sans-serif`.
- 기존 `ThemeBootstrapper` 삭제 · 기존 `lib/theme.ts` 삭제 (next-themes 대체).
- `i18n` 시스템 유지. `<html lang>`은 `useLocale()` 값을 사용하도록 변경.

### 4.6 Tailwind 설정

```ts
// web/tailwind.config.ts
content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
darkMode: "class",
theme: {
  extend: {
    colors: {
      paper: "rgb(var(--paper) / <alpha-value>)",
      "paper-deep": "rgb(var(--paper-deep) / <alpha-value>)",
      ink: "rgb(var(--ink) / <alpha-value>)",
      "ink-mute": "rgb(var(--ink-mute) / <alpha-value>)",
      "ink-faint": "rgb(var(--ink-faint) / <alpha-value>)",
      oxblood: "rgb(var(--oxblood) / <alpha-value>)",
      gold: "rgb(var(--gold) / <alpha-value>)",
      moss: "rgb(var(--moss) / <alpha-value>)",
      "stone-black": "rgb(var(--stone-black) / <alpha-value>)",
      "stone-white": "rgb(var(--stone-white) / <alpha-value>)",
    },
    fontFamily: {
      serif: ["var(--font-serif)", "Georgia", "serif"],
      sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      mono: ["var(--font-mono)", "ui-monospace", "monospace"],
    },
    letterSpacing: { label: "0.16em" },
    transitionTimingFunction: { stone: "cubic-bezier(.2,.7,.2,1)" },
  },
},
```

`globals.css`에는 light/dark `:root` 변수 블록 2세트와 `@layer base`에 typography utility (`.display-xl`, `.data`, `.label` 등) 정의.

## 5. 화면별 재디자인

### 5.1 TopNav (`components/TopNav.tsx` 재작성)

- 좌: `<BrandMark size={20}/>` + 세리프 워드마크 "Baduk" + 얇은 1px 세로 규칙 + Plex Mono "Vol. I"
- 중: (비어 있음 — 내비 링크는 우측 드롭다운으로)
- 우: 게임 시작 CTA (로그인 상태일 때) · 사용자 드롭다운 (DropdownMenu — 프로필·기보·설정·로그아웃) · 언어 드롭다운(ko/en) · 테마 토글 아이콘(Sun/Moon/Laptop)
- 높이 56px, 배경 paper, 하단 1px ink-faint
- 스크롤 시 paper 배경 유지(고정이 아닌 문서 흐름의 일부로 설계 — 장식 피함)

### 5.2 Home (`app/page.tsx` 재작성)

- `<Hero title="바둑, 조용한 승부" subtitle="KataGo Human-SL과 두는 한국식 바둑. 9×9 · 13×13 · 19×19." volume="Vol. I"/>`
- CTA: "새 대국" `<Button>` (ink bg) + 보조 "기보 보기" (ghost)
- 하단 3-column grid: "최근 대국" (최근 3개 기보 카드) / "프로파일" / "가이드"
- 비로그인 상태: 로그인 / 가입 유도 + 기능 3단 소개
- 로그인·비로그인 각각 빈 상태 포함

### 5.3 New Game (`app/game/new/page.tsx` 재작성)

- 좌측 2/3: 3단 스텝(상대 랭크 → 보드 크기 → 핸디캡)
  - 스텝별 라벨 + 선택 컨트롤(기존 Picker들을 editorial 프리미티브로 래핑)
  - 규칙선으로 스텝 구분
- 우측 1/3: "대국 요약" 카드 — 실시간으로 선택값 반영, 최하단 "대국 시작" Button
- 모바일: 단일 컬럼, 요약 카드가 고정 바텀 시트
- 기존 `RankPicker`/`BoardSizePicker`/`HandicapPicker`는 내부 UI만 재작성 (props 계약 유지)

### 5.4 Play (`app/game/play/[id]/page.tsx` 재작성)

레이아웃:
```
[TopNav 56px]
[───────────── 1px ink-faint ─────────────]
┌─ 2/3 column ──────────────────┬─ 1/3 column 280px ──┐
│ <PlayerCaption/> (백, 상단)    │ <StatFigure/> 승률  │
│                                │ <DataBlock/> 수순   │
│     <Board/> (중앙 정렬)       │ <DataBlock/> 시간   │
│                                │ <DataBlock/> 포획   │
│ <PlayerCaption/> (흑, 하단)    │ ─── LAST MOVES ──── │
│                                │ <MoveList/>         │
├────────────────────────────────┴─────────────────────┤
│  <GameControls/> — Pass(P) Resign(R) Undo(U) Hint(H)│
└──────────────────────────────────────────────────────┘
```
- `<Board/>` 재작업: 보드 배경 paper-deep, 격자선 ink, 좌표 라벨 Plex Mono ink-mute, 돌 placement 시 300ms stone transition, last-move 표시 oxblood 1px ring, hover 프리뷰 반투명.
- `<AnalysisOverlay/>` → Hint 클릭 시 상위 3수 oxblood 점선 마커 + 순위 배지.
- `<MoveList/>` 신규 — mono 좌표 목록, 현재 수는 ink-faint 배경, SGF 순번 클릭 시 리뷰 모드로.
- 미커밋 작업 병합: `lib/soundfx.ts` 그대로 유지(신규 파일). Board 반응형 `maxWidth`는 토큰으로 대체 불가한 레이아웃 제약 → 인라인 style 예외 허용, `design-token-check.sh`는 이 경로를 무시하도록 구성.
- 키보드: P/R/U/H 단축키 + `KeybindHint`.
- 모바일: 세로 스택. 데이터 패널은 접이식 Sheet(우측에서 슬라이드).

### 5.5 Review (`app/game/review/[id]/page.tsx` 재작성)

- 상단 `<Hero/>` 축소 버전 + 결과 요약(승리 · 최종 점수)
- 보드 + 타임라인 스크러버(얇은 규칙선 + 현재 수 ink 마커 + 클릭 가능)
- 키보드: ← → (수 이동), Home/End, 스페이스(재생/정지 — 추후)
- 우측 패널: 수별 분석(승률 그래프 + KataGo top3 — 기존 로직 유지)
- 하단: SGF 다운로드 Button + 공유 URL 복사

### 5.6 Login / Signup

- 2-column: 좌 paper-deep 배경에 세리프 브랜드 + 한 줄 카피 + 작은 BrandMark. 우 폼.
- Input 프리미티브 + Label + 필드별 에러 (오류는 `aria-invalid` + oxblood 하단 텍스트)
- 로그인 실패 시 Sonner toast
- 비밀번호 최소 길이 등 클라이언트 밸리데이션 추가

### 5.7 History (`app/history/page.tsx` 재작성)

- 신문 인덱스 테이블: 날짜 · 상대 · 결과 · 수순 · 액션
- 헤더는 uppercase label, 행 구분은 1px ink-faint
- 필터: 결과(승/패) · 보드 크기 · 기간 — DropdownMenu
- 페이지네이션 (기존 API 계약 준수)
- 빈 상태: `<EmptyState/>` — "아직 대국이 없습니다. 첫 대국을 시작하세요."

### 5.8 Settings (`app/settings/page.tsx` 재작성)

- 섹션: 계정 / 대국 / 표시 / 데이터
- 표시 섹션: 테마 토글(`<ToggleGroup>` — Day/Night/System), 언어(`<Select>` ko/en)
- 대국 섹션: 기본 보드 크기·핸디캡·확인 대화상자 선호도
- 각 섹션은 카드(paper-deep, 1px border) + 섹션 제목(h2)

### 5.9 404 · 에러 바운더리

- `app/not-found.tsx` 신규 — `<EmptyState/>`, 홈·히스토리 CTA
- `app/error.tsx` 신규 — 동일 구조 + 재시도 Button
- `app/global-error.tsx` — 최소 fallback (폰트 로딩 실패 시에도 작동)

## 6. 구현 단계

### Phase 1 — Foundation (기반)

1. 의존성 설치 (§4.2)
2. `lib/fonts.ts` + `app/layout.tsx` 폰트 로딩 + Pretendard link
3. `app/globals.css` 토큰·타이포 레이어 재작성
4. `tailwind.config.ts` 토큰 매핑 재작성
5. `lib/tokens.ts` · `lib/cn.ts` 유틸
6. `components/ui/` 12종 복붙 + Editorial 재스타일링 (§4.3)
7. `components/editorial/` 10종 프리미티브 작성 (§4.4)
8. `next-themes` ThemeProvider 도입, 기존 `ThemeBootstrapper`/`lib/theme.ts` 제거
9. `Sonner` Toaster 전역 마운트
10. `/dev/components` 내부 카탈로그 페이지 (dev 빌드만, 수동 회귀 시각 테스트용)

### Phase 2 — Core Flow

11. TopNav 재작성 (BrandMark 포함)
12. Home 재작성
13. New Game 재작성 + Picker 프리미티브 재스타일링
14. Play 재작성 + Board 재작업 (미커밋 변경 병합) + MoveList 신규 + AnalysisOverlay 재작업
15. Review 재작성 + 타임라인 스크러버
16. 기존 Vitest/Playwright 테스트 통과 확인 + Playwright 주요 화면 스크린샷 추가

### Phase 3 — Peripheral

17. Login/Signup 재작성
18. History 재작성
19. Settings 재작성 (테마 토글 포함)
20. 404 + error 바운더리

### Phase 4 — Polish

21. `@axe-core/react` dev 감사 → 이슈 수정
22. 키보드 내비게이션 엔드투엔드 검증 + `KeybindHint` 배치
23. 모바일 브레이크포인트 최종 조정 (375px, 768px, 1024px)
24. Lighthouse 데스크톱/모바일 점수 확인
25. README 스크린샷 갱신 (홈·Play·Review)
26. CHANGELOG `0.3.0` 항목 추가

## 7. 테스트 전략

- **Vitest**: 기존 단위 테스트(보드 로직·i18n) 전부 유지. 새 Editorial 프리미티브는 스냅샷 테스트만 (구조 검증).
- **Playwright**: 기존 E2E 시나리오(새 게임·대국·리뷰) 유지. 시각 회귀용 스크린샷 추가 — 주요 4화면 × 2 테마 = 8샷.
- **접근성**: `@axe-core/react` dev 전용. CI에는 포함하지 않음 (성능·노이즈).
- **수동 체크리스트** (Phase 4):
  - [ ] 키보드만으로 로그인→새 게임→착수→기권 가능
  - [ ] `prefers-color-scheme` 전환 시 플래시 없음
  - [ ] 모바일 375px에서 보드 + 컨트롤 시각 겹침 없음
  - [ ] 한글 + 영문 혼용 텍스트 베이스라인 정렬 자연스러움
  - [ ] Sonner 토스트 접근성(role=status) 확인

## 8. 위험·완화

| 위험 | 완화 |
|---|---|
| Pretendard CDN 장애 | `font-display: swap` + fallback 체인 `Pretendard Variable, Pretendard, -apple-system, sans-serif` |
| SSR 테마 플래시 | `next-themes` `attribute="class"` + `<script dangerouslySetInnerHTML>` 부트스트랩 |
| shadcn 컴포넌트 스타일 오염 | 복붙 직후 모든 `cn()` 병합 지점을 순회하며 토큰으로 재작성. Radix `data-state=open/closed` 전환은 `globals.css`에 커스텀 keyframes 4개(fade-in/out, slide-in/out)로 정의 (tailwindcss-animate 대체) |
| 보드 재작업 회귀 | Playwright 시각 스크린샷 + Vitest 기존 단위 테스트 |
| 번역 누락 | `lib/i18n/ko.json`/`en.json` 동시 수정 PR 규칙 (Phase별 체크) |
| Lighthouse Performance 하락 | 폰트 `next/font/google` + `display: "swap"` + 이미지 사용 자제 |
| 한국어 타이포 높이 차 | Pretendard는 라틴 베이스라인 정렬 양호. Newsreader와 혼용 시 옵티컬 미세조정 `font-feature-settings: "palt"` 필요 시 추가 |

## 9. 영향 받지 않는 부분

- `backend/` 전부
- `web/store/` Zustand 상태 — 시그니처 유지
- `web/lib/api.ts` · `ws.ts` · `board.ts` · `sgf.ts` · `soundfx.ts` · `i18n/`
- 라우트 경로 (`/`, `/login`, `/signup`, `/game/new`, `/game/play/[id]`, `/game/review/[id]`, `/history`, `/settings`)
- WS 프로토콜·REST 스키마
- Docker 빌드·배포

## 10. 산출물

- `web/package.json` 의존성 업데이트
- `web/tailwind.config.ts` · `web/app/globals.css` 재작성
- `web/lib/{tokens,fonts,cn}.ts` 신규
- `web/components/ui/` 12종 신규
- `web/components/editorial/` 10종 신규 (+ icons/)
- 9개 화면 + 404 + error 재구성
- Playwright 시각 스크린샷 8장
- CHANGELOG `0.3.0` 엔트리
- README 스크린샷 업데이트

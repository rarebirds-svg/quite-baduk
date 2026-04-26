# UI/UX 업리프트 Phase 2 — Core Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the five core-flow screens (TopNav, Home, New Game, Play, Review) using the Editorial Hardcover primitives built in Phase 1, preserving all existing functionality (WS protocol, REST shapes, game rules).

**Architecture:** Screens compose `components/ui/` (shadcn) + `components/editorial/` primitives. Sub-components (Board, pickers, GameControls, AnalysisOverlay) get visual rewrites while keeping their prop contracts. A new `MoveList` editorial primitive surfaces SGF-ordered moves. Data flow via existing Zustand `gameStore` and `openGameWS` is unchanged.

**Tech Stack:** Phase 1 stack (Next.js 14, Tailwind with token utilities, next-themes, Radix/shadcn, Sonner, Lucide). No new runtime dependencies.

**Prereqs:** Phase 1 branch `feat/ui-ux-phase-1-foundation` merged (or current branch). `/dev/components` catalog accessible for visual reference.

---

## Dependency Graph (for parallel dispatch)

```
T1 TopNav ──────── (no dependents in Phase 2)

T2 Board.tsx ─────┬──> T12 Play
                  └──> T13 Review

T3 MoveList ──────┬──> T12 Play
                  └──> T13 Review

T4 RankPicker ────┐
T5 BoardSizePkr ──┼──> T11 NewGame
T6 HandicapPkr ───┘

T7 AnalysisOverlay ──> T12 Play, T13 Review
T8 GameControls ─────> T12 Play
T9 ScorePanel delete ─ (T12 Play integrates score inline)

T10 Home (no component deps)

T14 i18n key additions ──> T10-T13 (run before screens)

T15 Playwright snapshots ──> after all screens
T16 Final verification ──> after T15
```

**Parallelizable groups:**
- **Group α (after T1 done):** T2, T3, T4, T5, T6, T7, T8, T9, T10, T14 — all independent of each other
- **Group β (after group α):** T11 (needs T4/T5/T6), T12 (needs T2/T3/T7/T8), T13 (needs T2/T3/T7) — all three run parallel
- **Group γ:** T15 after β, T16 after T15

---

## Task 1 — TopNav Rewrite

**Files:**
- Modify: `web/components/TopNav.tsx` (full replacement)
- Modify: `web/lib/i18n/ko.json` + `en.json` (add `nav.volume` key)

- [ ] **Step 1: Add i18n key**

In `web/lib/i18n/ko.json` under `nav` object, add `"volume": "Vol. I"`. In `web/lib/i18n/en.json`, same key `"volume": "Vol. I"`.

- [ ] **Step 2: Rewrite TopNav**

Overwrite `web/components/TopNav.tsx`:
```typescript
"use client";
import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { Sun, Moon, Laptop } from "lucide-react";
import { useT, useLocale, setLocale } from "@/lib/i18n";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { BrandMark } from "@/components/editorial/BrandMark";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/cn";

export default function TopNav() {
  const t = useT();
  const [locale] = useLocale();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { user, setUser } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    (async () => {
      try {
        const me = await api<{
          id: number;
          email: string;
          display_name: string;
          preferred_rank?: string | null;
          locale?: string;
          theme?: string;
        }>("/api/auth/me");
        setUser(me);
      } catch {
        setUser(null);
      }
    })();
  }, [setUser]);

  const logout = async () => {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } catch {}
    setUser(null);
    router.push("/");
  };

  const ThemeIcon = theme === "system" ? Laptop : resolvedTheme === "dark" ? Moon : Sun;
  const nextTheme = theme === "light" ? "dark" : theme === "dark" ? "system" : "light";

  return (
    <nav className="border-b border-ink-faint bg-paper">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4">
        <Link href="/" className="flex items-center gap-2" aria-label={t("app.title")}>
          <BrandMark size={20} />
          <span className="font-serif text-lg font-semibold tracking-tight">Baduk</span>
          <span aria-hidden className="h-3 w-px bg-ink-faint" />
          <span className="font-mono text-[10px] uppercase tracking-label text-ink-mute">
            {t("nav.volume")}
          </span>
        </Link>

        <div className="ml-auto flex items-center gap-2">
          {user && (
            <Button asChild size="sm" variant="outline">
              <Link href="/game/new">{t("nav.newGame")}</Link>
            </Button>
          )}

          <button
            onClick={() => setLocale(locale === "ko" ? "en" : "ko")}
            aria-label="Toggle language"
            className="flex h-9 w-9 items-center justify-center border border-ink-faint font-mono text-[10px] font-semibold uppercase tracking-label text-ink-mute hover:bg-paper-deep"
          >
            {locale === "ko" ? "EN" : "KO"}
          </button>

          <button
            onClick={() => setTheme(nextTheme)}
            aria-label={`Theme: ${theme}`}
            className="flex h-9 w-9 items-center justify-center border border-ink-faint text-ink-mute hover:bg-paper-deep hover:text-ink"
          >
            <ThemeIcon size={16} strokeWidth={1.5} />
          </button>

          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-2">
                  <span aria-hidden className="h-2 w-2 rounded-full bg-ink" />
                  {user.display_name}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>{user.email}</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/history">{t("nav.history")}</Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/settings">{t("nav.settings")}</Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout}>{t("nav.logout")}</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <>
              <Button asChild size="sm" variant="ghost">
                <Link href="/login">{t("nav.login")}</Link>
              </Button>
              <Button asChild size="sm" variant="default">
                <Link href="/signup">{t("nav.signup")}</Link>
              </Button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
```

- [ ] **Step 3: Verify typecheck + dev renders**

Run:
```bash
cd web && npx tsc --noEmit
```
Expected: no errors. Open http://localhost:3000/ — TopNav shows BrandMark + "Baduk" serif wordmark + "Vol. I" + theme toggle cycles Day/Night/System icons.

- [ ] **Step 4: Commit**

```bash
git add web/components/TopNav.tsx web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "feat(web): Editorial TopNav — brand mark, Vol.I, theme cycle, user dropdown"
```

---

## Task 2 — Board.tsx Rewrite

**Files:**
- Modify: `web/components/Board.tsx` (full replacement, preserve existing prop signature)

Existing props to preserve: `{size, board, lastMove?, onClick?, disabled?, overlay?}`.

- [ ] **Step 1: Rewrite Board.tsx**

Overwrite `web/components/Board.tsx`:
```typescript
"use client";
import { COLS, starPoints } from "@/lib/board";
import { tokens } from "@/lib/tokens";

type OverlayColor = "primary" | "secondary" | "tertiary";
type OverlayItem = { x: number; y: number; color: OverlayColor | string; label?: string };

const OVERLAY_TOKEN: Record<OverlayColor, string> = {
  primary: "rgb(var(--oxblood))",
  secondary: "rgb(var(--ink-mute))",
  tertiary: "rgb(var(--ink-faint))",
};
const resolveOverlayColor = (c: OverlayColor | string): string =>
  c in OVERLAY_TOKEN ? OVERLAY_TOKEN[c as OverlayColor] : c; // allow legacy CSS colors until callers migrate

export default function Board({
  size,
  board,
  lastMove = null,
  onClick,
  disabled,
  overlay,
}: {
  size: number;
  board: string;
  lastMove?: { x: number; y: number } | null;
  onClick?: (x: number, y: number) => void;
  disabled?: boolean;
  overlay?: OverlayItem[];
}) {
  const CELL = 30;
  const pad = CELL;
  const W = CELL * (size - 1) + pad * 2;
  const pts = [...Array(size).keys()].map((i) => pad + i * CELL);
  const stars = starPoints(size);

  const handleClick = (evt: React.MouseEvent<SVGRectElement, MouseEvent>) => {
    if (!onClick || disabled) return;
    const svg = (evt.currentTarget.ownerSVGElement as SVGSVGElement | null);
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const scale = W / rect.width;
    const localX = (evt.clientX - rect.left) * scale;
    const localY = (evt.clientY - rect.top) * scale;
    const x = Math.round((localX - pad) / CELL);
    const y = Math.round((localY - pad) / CELL);
    if (x < 0 || x >= size || y < 0 || y >= size) return;
    onClick(x, y);
  };

  return (
    <svg
      viewBox={`0 0 ${W} ${W}`}
      width="100%"
      style={{ maxWidth: "min(90vh, 90vw, 900px)" }}
      className="block bg-paper-deep"
      role="img"
      aria-label={`${size}×${size} Go board`}
    >
      {/* Outer ink border */}
      <rect x={0.5} y={0.5} width={W - 1} height={W - 1} fill="none" stroke="rgb(var(--ink))" strokeWidth={1} />

      {/* Grid lines */}
      {pts.map((p, i) => (
        <g key={i}>
          <line x1={pad} y1={p} x2={W - pad} y2={p} stroke="rgb(var(--ink))" strokeWidth={i === 0 || i === size - 1 ? 1.25 : 0.75} />
          <line x1={p} y1={pad} x2={p} y2={W - pad} stroke="rgb(var(--ink))" strokeWidth={i === 0 || i === size - 1 ? 1.25 : 0.75} />
        </g>
      ))}

      {/* Star points */}
      {stars.map(([sx, sy], i) => (
        <circle key={`s-${i}`} cx={pad + sx * CELL} cy={pad + sy * CELL} r={2.5} fill="rgb(var(--ink))" />
      ))}

      {/* Column labels (top + bottom, Plex Mono via CSS class) */}
      {[...Array(size).keys()].map((i) => {
        const label = COLS[i];
        const x = pad + i * CELL;
        return (
          <g key={`c-${i}`} className="font-mono" fill="rgb(var(--ink-mute))" fontSize={10}>
            <text x={x} y={14} textAnchor="middle">{label}</text>
            <text x={x} y={W - 6} textAnchor="middle">{label}</text>
          </g>
        );
      })}
      {/* Row labels (left + right) */}
      {[...Array(size).keys()].map((i) => {
        const label = size - i;
        const y = pad + i * CELL + 3;
        return (
          <g key={`r-${i}`} className="font-mono" fill="rgb(var(--ink-mute))" fontSize={10}>
            <text x={10} y={y} textAnchor="middle">{label}</text>
            <text x={W - 10} y={y} textAnchor="middle">{label}</text>
          </g>
        );
      })}

      {/* Stones */}
      {Array.from(board).map((c, idx) => {
        if (c !== "B" && c !== "W") return null;
        const x = idx % size;
        const y = Math.floor(idx / size);
        const cx = pad + x * CELL;
        const cy = pad + y * CELL;
        const fill = c === "B" ? tokens.light["stone-black"] : tokens.light["stone-white"];
        const stroke = c === "W" ? "rgb(var(--ink))" : "transparent";
        return <circle key={`st-${idx}`} cx={cx} cy={cy} r={CELL * 0.45} fill={fill} stroke={stroke} strokeWidth={0.75} />;
      })}

      {/* Last move: oxblood ring */}
      {lastMove && (
        <circle
          cx={pad + lastMove.x * CELL}
          cy={pad + lastMove.y * CELL}
          r={CELL * 0.38}
          fill="none"
          stroke="rgb(var(--oxblood))"
          strokeWidth={1.5}
        />
      )}

      {/* Overlay markers (hints, analysis) */}
      {overlay?.map((o, i) => {
        const stroke = resolveOverlayColor(o.color);
        return (
          <g key={`ov-${i}`}>
            <circle
              cx={pad + o.x * CELL}
              cy={pad + o.y * CELL}
              r={CELL * 0.42}
              fill="none"
              stroke={stroke}
              strokeDasharray="3 2"
              strokeWidth={1.25}
            />
            {o.label && (
              <text
                x={pad + o.x * CELL}
                y={pad + o.y * CELL + 3}
                textAnchor="middle"
                className="font-mono"
                fontSize={9}
                fill={stroke}
              >
                {o.label}
              </text>
            )}
          </g>
        );
      })}

      {/* Click capture */}
      {onClick && (
        <rect
          x={0}
          y={0}
          width={W}
          height={W}
          fill="transparent"
          style={{ cursor: disabled ? "not-allowed" : "pointer" }}
          onClick={handleClick}
        />
      )}
    </svg>
  );
}
```

**Note:** The `overlay` prop's `color` field now accepts both the new semantic tokens `"primary"|"secondary"|"tertiary"` AND legacy arbitrary CSS strings (for backward compatibility with existing Play/Review). T12/T13 migrate call sites to semantic tokens; in the meantime no caller breaks.

- [ ] **Step 2: Verify existing board tests still pass**

```bash
cd web && npx vitest run tests/board.test.ts
```
Expected: 9 tests pass (unchanged, they test `lib/board.ts` not the component).

- [ ] **Step 3: Typecheck**

```bash
cd web && npx tsc --noEmit
```
Expected: no errors. The `color: OverlayColor | string` union keeps existing callers compiling.

- [ ] **Step 4: Commit**

```bash
git add web/components/Board.tsx
git commit -m "feat(web/Board): Editorial SVG board with ink gridlines, oxblood last-move ring"
```

---

## Task 3 — `editorial/MoveList` Primitive

**Files:**
- Create: `web/components/editorial/MoveList.tsx`
- Create: `web/tests/editorial/move-list.test.tsx`

- [ ] **Step 1: Write failing test**

Create `web/tests/editorial/move-list.test.tsx`:
```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MoveList, type MoveEntry } from "../../components/editorial/MoveList";

const moves: MoveEntry[] = [
  { number: 1, color: "B", coord: "E5" },
  { number: 2, color: "W", coord: "C3" },
  { number: 3, color: "B", coord: "pass" },
];

describe("MoveList", () => {
  it("renders all move rows", () => {
    render(<MoveList moves={moves} currentIndex={0} />);
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("E5")).toBeInTheDocument();
    expect(screen.getByText("C3")).toBeInTheDocument();
  });

  it("highlights the current move", () => {
    const { container } = render(<MoveList moves={moves} currentIndex={1} />);
    const active = container.querySelector('[data-current="true"]');
    expect(active?.textContent).toContain("C3");
  });

  it("renders pass as italic label", () => {
    render(<MoveList moves={moves} currentIndex={2} />);
    const passCell = screen.getByText("pass");
    expect(passCell.tagName.toLowerCase()).toBe("em");
  });

  it("fires onSelect when a move is clicked", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    let picked = -1;
    render(<MoveList moves={moves} currentIndex={0} onSelect={(i) => (picked = i)} />);
    await user.click(screen.getByText("C3"));
    expect(picked).toBe(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && npx vitest run tests/editorial/move-list.test.tsx
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement MoveList**

Create `web/components/editorial/MoveList.tsx`:
```typescript
import * as React from "react";
import { cn } from "@/lib/cn";

export interface MoveEntry {
  number: number;
  color: "B" | "W";
  coord: string; // GTP ("E5") or "pass" or "resign"
}

export interface MoveListProps extends React.HTMLAttributes<HTMLOListElement> {
  moves: MoveEntry[];
  currentIndex: number;
  onSelect?: (index: number) => void;
}

export const MoveList = React.forwardRef<HTMLOListElement, MoveListProps>(
  ({ moves, currentIndex, onSelect, className, ...props }, ref) => (
    <ol
      ref={ref}
      className={cn("flex flex-col font-mono text-xs text-ink", className)}
      {...props}
    >
      {moves.map((m, i) => {
        const isCurrent = i === currentIndex;
        const isSpecial = m.coord === "pass" || m.coord === "resign";
        return (
          <li
            key={`${m.number}-${m.color}`}
            data-current={isCurrent}
            className={cn(
              "grid grid-cols-[2.5rem_1rem_1fr] items-baseline gap-2 px-2 py-1.5 border-b border-ink-faint/40",
              isCurrent && "bg-paper-deep",
              onSelect && "cursor-pointer hover:bg-paper-deep"
            )}
            onClick={onSelect ? () => onSelect(i) : undefined}
          >
            <span className="text-ink-mute tabular-nums">{m.number}</span>
            <span aria-hidden>
              <span className={cn("inline-block h-2 w-2 rounded-full", m.color === "B" ? "bg-stone-black" : "bg-stone-white border border-ink")} />
            </span>
            <span className={cn(isCurrent && "text-oxblood font-semibold")}>
              {isSpecial ? <em className="not-italic text-ink-mute">{m.coord}</em> : m.coord}
            </span>
          </li>
        );
      })}
    </ol>
  )
);
MoveList.displayName = "MoveList";
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd web && npx vitest run tests/editorial/move-list.test.tsx
```
Expected: 4 tests passed.

- [ ] **Step 5: Commit**

```bash
git add web/components/editorial/MoveList.tsx web/tests/editorial/move-list.test.tsx
git commit -m "feat(web/editorial): MoveList (mono-spaced SGF-ordered move log with active highlight)"
```

---

## Task 4 — RankPicker Rewrite

**Files:**
- Modify: `web/components/RankPicker.tsx` (full replacement, preserve `RANKS` export and `Rank` type + prop shape `{value, onChange}`)

- [ ] **Step 1: Rewrite**

Overwrite `web/components/RankPicker.tsx`:
```typescript
"use client";
import { useT } from "@/lib/i18n";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";

export const RANKS = ["18k", "15k", "12k", "10k", "7k", "5k", "3k", "1k", "1d", "3d", "5d", "7d"] as const;
export type Rank = (typeof RANKS)[number];

export interface RankPickerProps {
  value: Rank;
  onChange: (rank: Rank) => void;
  label?: string;
}

export default function RankPicker({ value, onChange, label }: RankPickerProps) {
  const t = useT();
  const resolvedLabel = label ?? t("game.rank");
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor="rank-picker">{resolvedLabel}</Label>
      <Select value={value} onValueChange={(v) => onChange(v as Rank)}>
        <SelectTrigger id="rank-picker" className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {RANKS.map((r) => (
            <SelectItem key={r} value={r}>
              {r}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/RankPicker.tsx
git commit -m "feat(web): RankPicker on Select primitive, Label + editorial styling"
```

---

## Task 5 — BoardSizePicker Rewrite

**Files:**
- Modify: `web/components/BoardSizePicker.tsx` (full replacement)

- [ ] **Step 1: Rewrite**

Overwrite `web/components/BoardSizePicker.tsx`:
```typescript
"use client";
import { SUPPORTED_SIZES, type BoardSize } from "@/lib/board";
import { useT } from "@/lib/i18n";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Label } from "@/components/ui/label";

export interface BoardSizePickerProps {
  value: BoardSize;
  onChange: (size: BoardSize) => void;
  label?: string;
}

export default function BoardSizePicker({ value, onChange, label }: BoardSizePickerProps) {
  const t = useT();
  const resolvedLabel = label ?? t("game.boardSize");
  return (
    <div className="flex flex-col gap-2">
      <Label>{resolvedLabel}</Label>
      <ToggleGroup
        type="single"
        value={String(value)}
        onValueChange={(v) => v && onChange(Number(v) as BoardSize)}
      >
        {SUPPORTED_SIZES.map((s) => (
          <ToggleGroupItem key={s} value={String(s)}>
            {s}×{s}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/BoardSizePicker.tsx
git commit -m "feat(web): BoardSizePicker on ToggleGroup (9×9 / 13×13 / 19×19)"
```

---

## Task 6 — HandicapPicker Rewrite

**Files:**
- Modify: `web/components/HandicapPicker.tsx` (full replacement)

- [ ] **Step 1: Rewrite**

Overwrite `web/components/HandicapPicker.tsx`:
```typescript
"use client";
import { useT } from "@/lib/i18n";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";

const HANDICAP_BY_SIZE: Record<number, number[]> = {
  9: [2, 3, 4, 5],
  13: [2, 3, 4, 5, 6, 7, 8, 9],
  19: [2, 3, 4, 5, 6, 7, 8, 9],
};

export interface HandicapPickerProps {
  boardSize: number;
  value: number;
  onChange: (n: number) => void;
  label?: string;
}

export default function HandicapPicker({ boardSize, value, onChange, label }: HandicapPickerProps) {
  const t = useT();
  const valid = HANDICAP_BY_SIZE[boardSize] ?? [];
  const resolvedLabel = label ?? t("game.handicap");
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor="handicap-picker">{resolvedLabel}</Label>
      <Select value={String(value)} onValueChange={(v) => onChange(Number(v))}>
        <SelectTrigger id="handicap-picker" className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="0">{t("game.handicapNone")}</SelectItem>
          {valid.map((n) => (
            <SelectItem key={n} value={String(n)}>
              {t("game.handicapStones", { n: String(n) })}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
```

**Prereq:** `ko.json`/`en.json` must have `game.handicapNone` and `game.handicapStones` keys. If absent:
- ko: `"handicapNone": "평균 (0)"`, `"handicapStones": "{n} 점"`
- en: `"handicapNone": "Even (0)"`, `"handicapStones": "{n} stones"`

- [ ] **Step 2: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/HandicapPicker.tsx web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "feat(web): HandicapPicker on Select (None + valid stone counts)"
```

---

## Task 7 — AnalysisOverlay Rewrite

**Files:**
- Modify: `web/components/AnalysisOverlay.tsx` (full replacement, preserve prop shape)

- [ ] **Step 1: Rewrite**

Overwrite `web/components/AnalysisOverlay.tsx`:
```typescript
import { StatFigure } from "@/components/editorial/StatFigure";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { cn } from "@/lib/cn";

export interface AnalysisOverlayProps {
  topMoves: { move: string; winrate: number; visits: number }[];
  winrate: number;
  className?: string;
}

export default function AnalysisOverlay({ topMoves, winrate, className }: AnalysisOverlayProps) {
  const pct = (winrate * 100).toFixed(1);
  const trend = winrate > 0.5 ? "up" : winrate < 0.5 ? "down" : null;
  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <StatFigure value={pct} unit="%" label="WIN RATE" trend={trend} />
      <RuleDivider label="TOP MOVES" />
      <ol className="flex flex-col font-mono text-xs">
        {topMoves.slice(0, 5).map((m, i) => (
          <li
            key={m.move}
            className="grid grid-cols-[1.25rem_1fr_4rem_auto] items-baseline gap-2 border-b border-ink-faint/40 py-1.5"
          >
            <span className="font-sans text-[10px] font-semibold uppercase tracking-label text-oxblood">
              {i + 1}
            </span>
            <span className="text-ink font-semibold">{m.move}</span>
            <span className="text-ink-mute tabular-nums text-right">
              {(m.winrate * 100).toFixed(1)}%
            </span>
            <span className="text-ink-faint tabular-nums text-right">{m.visits}v</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/AnalysisOverlay.tsx
git commit -m "feat(web): AnalysisOverlay with StatFigure + mono top-moves list"
```

---

## Task 8 — GameControls Rewrite

**Files:**
- Modify: `web/components/GameControls.tsx`

- [ ] **Step 1: Rewrite**

Overwrite `web/components/GameControls.tsx`:
```typescript
"use client";
import { Button } from "@/components/ui/button";
import { KeybindHint } from "@/components/editorial/KeybindHint";
import { IconPass, IconResign, IconUndo, IconHint } from "@/components/editorial/icons";
import { useT } from "@/lib/i18n";
import { useEffect } from "react";

export interface GameControlsProps {
  onPass: () => void;
  onResign: () => void;
  onUndo: () => void;
  onHint: () => void;
  disabled?: boolean;
}

export default function GameControls({ onPass, onResign, onUndo, onHint, disabled }: GameControlsProps) {
  const t = useT();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (disabled) return;
      if (e.target && (e.target as HTMLElement).tagName.match(/INPUT|TEXTAREA/)) return;
      const k = e.key.toLowerCase();
      if (k === "p") { e.preventDefault(); onPass(); }
      if (k === "r") { e.preventDefault(); onResign(); }
      if (k === "u") { e.preventDefault(); onUndo(); }
      if (k === "h") { e.preventDefault(); onHint(); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onPass, onResign, onUndo, onHint, disabled]);

  return (
    <div className="flex flex-col gap-2 border-t border-ink-faint pt-3">
      <div className="grid grid-cols-4 gap-2">
        <Button onClick={onPass} disabled={disabled} variant="outline" className="flex flex-col h-auto py-3 gap-1">
          <IconPass />
          <span className="font-sans text-xs font-semibold uppercase tracking-label">{t("game.pass")}</span>
        </Button>
        <Button onClick={onUndo} disabled={disabled} variant="outline" className="flex flex-col h-auto py-3 gap-1">
          <IconUndo />
          <span className="font-sans text-xs font-semibold uppercase tracking-label">{t("game.undo")}</span>
        </Button>
        <Button onClick={onHint} disabled={disabled} variant="outline" className="flex flex-col h-auto py-3 gap-1 text-oxblood border-oxblood">
          <IconHint />
          <span className="font-sans text-xs font-semibold uppercase tracking-label">{t("game.hint")}</span>
        </Button>
        <Button onClick={onResign} disabled={disabled} variant="destructive" className="flex flex-col h-auto py-3 gap-1">
          <IconResign />
          <span className="font-sans text-xs font-semibold uppercase tracking-label">{t("game.resign")}</span>
        </Button>
      </div>
      <div className="flex gap-4 justify-center">
        <KeybindHint keys={["P"]} description={t("game.pass")} />
        <KeybindHint keys={["U"]} description={t("game.undo")} />
        <KeybindHint keys={["H"]} description={t("game.hint")} />
        <KeybindHint keys={["R"]} description={t("game.resign")} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/GameControls.tsx
git commit -m "feat(web): GameControls with Go icons, KeybindHints, P/R/U/H shortcuts"
```

---

## Task 9 — Delete Standalone ScorePanel

**Rationale:** The Editorial Play layout integrates captures into the right data panel via `<DataBlock>`. `<ScorePanel>` as a separate top-stripe is redundant in the new design and gets removed. Existing call site in Play page is rewritten in T12.

**Files:**
- Delete: `web/components/ScorePanel.tsx`

- [ ] **Step 1: Delete file**

```bash
rm web/components/ScorePanel.tsx
```

- [ ] **Step 2: Verify no other references**

```bash
cd web && grep -r "ScorePanel" --include="*.tsx" --include="*.ts"
```
Expected: only reference is in `app/game/play/[id]/page.tsx` (to be rewritten in T12). If anywhere else, add to T12's Play rewrite.

- [ ] **Step 3: Commit**

```bash
git add -A web/components/ScorePanel.tsx
git commit -m "chore(web): remove standalone ScorePanel (captures inline in Play data panel)"
```

---

## Task 10 — Home Rewrite

**Files:**
- Modify: `web/app/page.tsx`
- Modify: `web/lib/i18n/ko.json` + `en.json` (ensure `home.heroSubtitle`, `home.ctaNew`, `home.ctaReview`, `home.sectionRecent`, `home.sectionEmpty` exist; add if missing)

- [ ] **Step 1: Add i18n keys**

Verify / add keys to `web/lib/i18n/ko.json` under `home`:
```json
{
  "home": {
    "heroSubtitle": "KataGo Human-SL과 두는 한국식 바둑. 9×9 · 13×13 · 19×19.",
    "volume": "Vol. I",
    "ctaNew": "새 대국 시작",
    "ctaReview": "최근 기보",
    "sectionRecent": "최근 대국",
    "sectionEmpty": "아직 대국이 없습니다. 첫 대국을 시작하세요.",
    "guestSignup": "가입하고 기보를 저장하세요"
  }
}
```
`web/lib/i18n/en.json` under `home`:
```json
{
  "home": {
    "heroSubtitle": "Play Korean-rules Go against KataGo Human-SL. 9×9 · 13×13 · 19×19.",
    "volume": "Vol. I",
    "ctaNew": "New game",
    "ctaReview": "Recent games",
    "sectionRecent": "Recent games",
    "sectionEmpty": "No games yet. Start your first.",
    "guestSignup": "Sign up to save your games"
  }
}
```

- [ ] **Step 2: Rewrite `app/page.tsx`**

Overwrite `web/app/page.tsx`:
```typescript
"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useT } from "@/lib/i18n";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { Hero } from "@/components/editorial/Hero";
import { EmptyState } from "@/components/editorial/EmptyState";
import { BrandMark } from "@/components/editorial/BrandMark";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type RecentGame = {
  id: number;
  board_size: number;
  opponent_rank: string;
  result: string;
  created_at: string;
};

export default function Home() {
  const t = useT();
  const { user } = useAuthStore();
  const [recent, setRecent] = useState<RecentGame[] | null>(null);

  useEffect(() => {
    if (!user) return;
    (async () => {
      try {
        const res = await api<{ games: RecentGame[] }>("/api/games?limit=3");
        setRecent(res.games);
      } catch {
        setRecent([]);
      }
    })();
  }, [user]);

  return (
    <div className="flex flex-col gap-10 py-6">
      <Hero
        title="바둑, 조용한 승부"
        subtitle={t("home.heroSubtitle")}
        volume={t("home.volume")}
      />

      <div className="flex flex-wrap gap-3">
        <Button asChild size="lg">
          <Link href={user ? "/game/new" : "/signup"}>{user ? t("home.ctaNew") : t("home.guestSignup")}</Link>
        </Button>
        {user && (
          <Button asChild size="lg" variant="ghost">
            <Link href="/history">{t("home.ctaReview")}</Link>
          </Button>
        )}
      </div>

      {user && (
        <section className="flex flex-col gap-4">
          <RuleDivider label={t("home.sectionRecent")} weight="strong" />
          {recent === null ? (
            <div className="h-24 border border-ink-faint bg-paper-deep" aria-busy />
          ) : recent.length === 0 ? (
            <EmptyState
              icon={<BrandMark size={32} className="opacity-40" />}
              title={t("home.sectionEmpty")}
              action={
                <Button asChild>
                  <Link href="/game/new">{t("home.ctaNew")}</Link>
                </Button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {recent.map((g) => (
                <Link key={g.id} href={`/game/review/${g.id}`}>
                  <Card className="transition-colors hover:bg-paper-deep/70">
                    <CardHeader>
                      <CardTitle>
                        {g.board_size} × {g.board_size} · {g.result || "진행중"}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="font-mono text-xs text-ink-mute">
                        {new Date(g.created_at).toISOString().slice(0, 10)} · 상대 {g.opponent_rank}
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Typecheck + dev smoke**

```bash
cd web && npx tsc --noEmit
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/
```
Expected: 200.

- [ ] **Step 4: Commit**

```bash
git add web/app/page.tsx web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "feat(web): Home — Editorial hero + CTA + recent-games grid + empty state"
```

---

## Task 11 — New Game Rewrite

**Files:**
- Modify: `web/app/game/new/page.tsx`

**Prereq:** T4, T5, T6 complete.

- [ ] **Step 1: Rewrite**

Overwrite `web/app/game/new/page.tsx`:
```typescript
"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useT } from "@/lib/i18n";
import { api, ApiError } from "@/lib/api";
import type { BoardSize } from "@/lib/board";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { DataBlock } from "@/components/editorial/DataBlock";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Label } from "@/components/ui/label";
import RankPicker, { type Rank } from "@/components/RankPicker";
import BoardSizePicker from "@/components/BoardSizePicker";
import HandicapPicker from "@/components/HandicapPicker";
import { toast } from "sonner";

const HANDICAP_VALID: Record<number, number[]> = {
  9: [0, 2, 3, 4, 5],
  13: [0, 2, 3, 4, 5, 6, 7, 8, 9],
  19: [0, 2, 3, 4, 5, 6, 7, 8, 9],
};

export default function NewGamePage() {
  const t = useT();
  const router = useRouter();
  const [boardSize, setBoardSize] = useState<BoardSize>(9);
  const [rank, setRank] = useState<Rank>("5k");
  const [handicap, setHandicap] = useState(0);
  const [userColor, setUserColor] = useState<"black" | "white">("black");
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        await api("/api/auth/me");
        setAuthed(true);
      } catch {
        setAuthed(false);
        router.push("/login?next=/game/new");
      }
    })();
  }, [router]);

  useEffect(() => {
    // Reset handicap when board size changes if invalid
    if (!HANDICAP_VALID[boardSize].includes(handicap)) setHandicap(0);
  }, [boardSize, handicap]);

  const onCreate = async () => {
    setBusy(true);
    try {
      const res = await api<{ id: number }>("/api/games", {
        method: "POST",
        body: JSON.stringify({
          ai_rank: rank,
          handicap,
          user_color: userColor,
          board_size: boardSize,
        }),
      });
      router.push(`/game/play/${res.id}`);
    } catch (e: unknown) {
      toast.error(t(`errors.${(e as ApiError).code || "validation"}`));
    } finally {
      setBusy(false);
    }
  };

  if (authed === null) return null;

  return (
    <div className="flex flex-col gap-8 py-6">
      <Hero title={t("game.newGame")} subtitle={t("game.newGameSubtitle")} />

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[2fr_1fr]">
        <div className="flex flex-col gap-8">
          <section className="flex flex-col gap-4">
            <RuleDivider label="상대" />
            <RankPicker value={rank} onChange={setRank} />
          </section>

          <section className="flex flex-col gap-4">
            <RuleDivider label="판" />
            <BoardSizePicker value={boardSize} onChange={setBoardSize} />
          </section>

          <section className="flex flex-col gap-4">
            <RuleDivider label="핸디캡" />
            <HandicapPicker boardSize={boardSize} value={handicap} onChange={setHandicap} />
          </section>

          <section className="flex flex-col gap-4">
            <RuleDivider label="선택" />
            <div className="flex flex-col gap-2">
              <Label>{t("game.yourColor")}</Label>
              <ToggleGroup
                type="single"
                value={userColor}
                onValueChange={(v) => v && setUserColor(v as "black" | "white")}
              >
                <ToggleGroupItem value="black">{t("game.black")}</ToggleGroupItem>
                <ToggleGroupItem value="white">{t("game.white")}</ToggleGroupItem>
              </ToggleGroup>
            </div>
          </section>
        </div>

        <aside>
          <Card>
            <CardContent className="flex flex-col gap-3 py-4">
              <div className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood">
                {t("game.summary")}
              </div>
              <DataBlock label={t("game.rank")} value={rank} />
              <DataBlock label={t("game.boardSize")} value={`${boardSize}×${boardSize}`} />
              <DataBlock label={t("game.handicap")} value={handicap === 0 ? t("game.handicapNone") : `${handicap}`} />
              <DataBlock label={t("game.yourColor")} value={userColor === "black" ? t("game.black") : t("game.white")} />
              <Button className="mt-4 w-full" size="lg" onClick={onCreate} disabled={busy}>
                {busy ? "…" : t("game.start")}
              </Button>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add missing i18n keys**

Ensure these exist in `ko.json` (add if missing):
- `game.newGame`: "새 대국"
- `game.newGameSubtitle`: "상대·판 크기·핸디캡을 선택하고 시작하세요."
- `game.yourColor`: "내 색"
- `game.black`: "흑"
- `game.white`: "백"
- `game.summary`: "대국 요약"
- `game.start`: "대국 시작"

And in `en.json` (add if missing):
- `game.newGame`: "New game"
- `game.newGameSubtitle`: "Pick opponent, size, and handicap to begin."
- `game.yourColor`: "Your color"
- `game.black`: "Black"
- `game.white`: "White"
- `game.summary`: "Summary"
- `game.start`: "Start"

- [ ] **Step 3: Typecheck + dev smoke**

```bash
cd web && npx tsc --noEmit
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/game/new
```
Expected: either 200 (if logged in) or redirect to `/login?next=/game/new` (if not). Either is success.

- [ ] **Step 4: Commit**

```bash
git add web/app/game/new/page.tsx web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "feat(web): New Game — editorial 4-section form + live summary card"
```

---

## Task 12 — Play Rewrite

**Files:**
- Modify: `web/app/game/play/[id]/page.tsx`

**Prereqs:** T2 (Board), T3 (MoveList), T7 (AnalysisOverlay), T8 (GameControls).

- [ ] **Step 1: Rewrite**

Overwrite `web/app/game/play/[id]/page.tsx`:
```typescript
"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { openGameWS, type GameWS } from "@/lib/ws";
import { useGameStore } from "@/store/gameStore";
import { useT } from "@/lib/i18n";
import { parseBoard, xyToGtp, gtpToXy, COLS } from "@/lib/board";
import { playStoneClick } from "@/lib/soundfx";
import Board from "@/components/Board";
import GameControls from "@/components/GameControls";
import AnalysisOverlay from "@/components/AnalysisOverlay";
import { PlayerCaption } from "@/components/editorial/PlayerCaption";
import { StatFigure } from "@/components/editorial/StatFigure";
import { DataBlock } from "@/components/editorial/DataBlock";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { MoveList, type MoveEntry } from "@/components/editorial/MoveList";
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

type HintState = {
  topMoves: { move: string; winrate: number; visits: number }[];
  winrate: number;
} | null;

export default function PlayPage() {
  const t = useT();
  const { id } = useParams<{ id: string }>();
  const state = useGameStore();
  const wsRef = useRef<GameWS | null>(null);
  const [hint, setHint] = useState<HintState>(null);
  const [moves, setMoves] = useState<MoveEntry[]>([]);
  const [confirmResign, setConfirmResign] = useState(false);

  useEffect(() => {
    if (!id) return;
    const gid = parseInt(id, 10);
    const ws = openGameWS(gid, (msg) => {
      if (msg.type === "state") {
        const next = parseBoard(msg.board);
        state.set({
          board: msg.board,
          boardSize: msg.board_size,
          toMove: msg.to_move,
          moveCount: msg.move_count,
          captures: msg.captures,
          lastAiMove: msg.last_ai_move,
          aiThinking: msg.ai_thinking,
          gameOver: msg.game_over,
          result: msg.result ?? null,
          error: null,
        });
        setMoves(
          msg.moves.map((m: { number: number; color: "B" | "W"; coord: string }) => ({
            number: m.number,
            color: m.color,
            coord: m.coord,
          }))
        );
      } else if (msg.type === "ai_move") {
        playStoneClick();
      } else if (msg.type === "game_over") {
        state.set({ gameOver: true, result: msg.result, error: null });
      } else if (msg.type === "error") {
        state.set({ error: msg.code });
        toast.error(t(`errors.${msg.code}`));
      }
    });
    wsRef.current = ws;
    return () => ws.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const onStoneClick = (x: number, y: number) => {
    if (state.gameOver || state.aiThinking || state.toMove !== "B") return;
    const coord = xyToGtp(x, y, state.boardSize);
    wsRef.current?.send({ type: "move", coord });
    playStoneClick();
  };

  const lastMove = useMemo(() => {
    if (!state.lastAiMove || state.lastAiMove === "pass") return null;
    const xy = gtpToXy(state.lastAiMove, state.boardSize);
    return xy ? { x: xy[0], y: xy[1] } : null;
  }, [state.lastAiMove, state.boardSize]);

  const hintOverlay = useMemo(() => {
    if (!hint) return undefined;
    return hint.topMoves.slice(0, 3).map((m, i) => {
      const xy = gtpToXy(m.move, state.boardSize);
      if (!xy) return null;
      return {
        x: xy[0],
        y: xy[1],
        color: (i === 0 ? "primary" : i === 1 ? "secondary" : "tertiary") as const,
        label: String(i + 1),
      };
    }).filter((x): x is NonNullable<typeof x> => x !== null);
  }, [hint, state.boardSize]);

  const onHint = async () => {
    try {
      const r = await fetch(`/api/games/${id}/analyze`, { method: "POST", credentials: "include" });
      if (!r.ok) throw new Error();
      const data = await r.json();
      setHint({ topMoves: data.top_moves, winrate: data.winrate });
    } catch {
      toast.error(t("errors.analysisFailed"));
    }
  };

  return (
    <div className="flex flex-col gap-4 py-4 md:grid md:grid-cols-[minmax(0,1fr)_280px] md:gap-8">
      <div className="flex flex-col gap-4">
        <PlayerCaption
          color="white"
          name="KataGo"
          rank={t("game.aiRank")}
          subtitle={state.aiThinking ? t("game.thinking") : ""}
        />
        <Board
          size={state.boardSize}
          board={state.board}
          lastMove={lastMove}
          onClick={onStoneClick}
          disabled={state.gameOver || state.aiThinking || state.toMove !== "B"}
          overlay={hintOverlay}
        />
        <PlayerCaption
          color="black"
          name={t("game.you")}
          rank={t("game.yourRank")}
          subtitle={state.toMove === "B" && !state.gameOver ? t("game.yourTurn") : ""}
        />

        <GameControls
          onPass={() => wsRef.current?.send({ type: "pass" })}
          onResign={() => setConfirmResign(true)}
          onUndo={() => wsRef.current?.send({ type: "undo" })}
          onHint={onHint}
          disabled={state.gameOver || state.aiThinking}
        />

        {state.gameOver && (
          <div className="border border-ink p-4 font-serif text-lg">
            {t("game.result")}: {state.result}
          </div>
        )}
      </div>

      <aside className="flex flex-col gap-6">
        {hint ? (
          <AnalysisOverlay topMoves={hint.topMoves} winrate={hint.winrate} />
        ) : (
          <StatFigure value={state.moveCount} label={t("game.move")} />
        )}
        <RuleDivider label={t("game.info")} />
        <DataBlock label={t("game.captures")} value={`● ${state.captures?.B ?? 0}  ○ ${state.captures?.W ?? 0}`} />
        <DataBlock label={t("game.toMove")} value={state.toMove === "B" ? t("game.black") : t("game.white")} />
        <RuleDivider label={t("game.moves")} />
        <div className="max-h-[40vh] overflow-y-auto border border-ink-faint">
          <MoveList moves={moves} currentIndex={moves.length - 1} />
        </div>
      </aside>

      <Dialog open={confirmResign} onOpenChange={setConfirmResign}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("game.confirmResignTitle")}</DialogTitle>
            <DialogDescription>{t("game.confirmResignDesc")}</DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirmResign(false)}>
              {t("game.cancel")}
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                wsRef.current?.send({ type: "resign" });
                setConfirmResign(false);
              }}
            >
              {t("game.resign")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
```

- [ ] **Step 2: Add missing i18n keys**

Ensure these keys in both `ko.json` and `en.json`:
- `game.aiRank`: "KataGo Human-SL" / "KataGo Human-SL"
- `game.you`: "나" / "You"
- `game.yourRank`: "플레이어" / "Player"
- `game.yourTurn`: "당신 차례" / "Your turn"
- `game.thinking`: "수를 읽는 중…" / "Thinking…"
- `game.result`: "결과" / "Result"
- `game.info`: "정보" / "INFO"
- `game.moves`: "기보" / "MOVES"
- `game.move`: "수" / "MOVE"
- `game.captures`: "따냄" / "CAPTURES"
- `game.toMove`: "차례" / "TO MOVE"
- `game.confirmResignTitle`: "기권하시겠습니까?" / "Resign?"
- `game.confirmResignDesc`: "현재 대국을 기권으로 종료합니다. 기보는 저장됩니다." / "End the game as a loss; the record is saved."
- `game.cancel`: "취소" / "Cancel"
- `errors.analysisFailed`: "분석을 가져올 수 없습니다." / "Unable to fetch analysis."

- [ ] **Step 3: Typecheck + build check**

```bash
cd web && npx tsc --noEmit && npm run build
```
Expected: clean compile + build.

- [ ] **Step 4: Commit**

```bash
git add web/app/game/play/[id]/page.tsx web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "feat(web): Play — Editorial 2-column layout + MoveList + Resign Dialog"
```

---

## Task 13 — Review Rewrite

**Files:**
- Modify: `web/app/game/review/[id]/page.tsx`

**Prereqs:** T2 (Board), T3 (MoveList), T7 (AnalysisOverlay).

- [ ] **Step 1: Rewrite**

Overwrite `web/app/game/review/[id]/page.tsx`:
```typescript
"use client";
import { useEffect, useMemo, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { parseBoard, gtpToXy, totalCells } from "@/lib/board";
import Board from "@/components/Board";
import AnalysisOverlay from "@/components/AnalysisOverlay";
import { Hero } from "@/components/editorial/Hero";
import { MoveList, type MoveEntry } from "@/components/editorial/MoveList";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { KeybindHint } from "@/components/editorial/KeybindHint";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

type MoveEntryRaw = { move_number: number; color: "B" | "W"; coord: string; is_undone: boolean };
type GameDetail = { id: number; board_size: number; moves: MoveEntryRaw[]; result: string; created_at: string };
type AnalysisResp = { winrate: number; top_moves: { move: string; winrate: number; visits: number }[] };

export default function ReviewPage() {
  const t = useT();
  const { id } = useParams<{ id: string }>();
  const [game, setGame] = useState<GameDetail | null>(null);
  const [index, setIndex] = useState(0);
  const [analysis, setAnalysis] = useState<AnalysisResp | null>(null);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const g = await api<GameDetail>(`/api/games/${id}`);
        setGame(g);
        setIndex(g.moves.length);
      } catch {
        toast.error(t("errors.notFound"));
      }
    })();
  }, [id, t]);

  const replayedBoard = useMemo(() => {
    if (!game) return "";
    const total = totalCells(game.board_size);
    const cells = new Array<string>(total).fill(".");
    for (let i = 0; i < index && i < game.moves.length; i++) {
      const m = game.moves[i];
      if (m.is_undone || m.coord === "pass" || m.coord === "resign") continue;
      const xy = gtpToXy(m.coord, game.board_size);
      if (!xy) continue;
      const [x, y] = xy;
      cells[y * game.board_size + x] = m.color;
    }
    return cells.join("");
  }, [game, index]);

  const lastMove = useMemo(() => {
    if (!game || index === 0) return null;
    const m = game.moves[index - 1];
    if (!m || m.is_undone || m.coord === "pass" || m.coord === "resign") return null;
    const xy = gtpToXy(m.coord, game.board_size);
    return xy ? { x: xy[0], y: xy[1] } : null;
  }, [game, index]);

  const moves: MoveEntry[] = useMemo(
    () =>
      (game?.moves ?? []).map((m) => ({
        number: m.move_number,
        color: m.color,
        coord: m.coord,
      })),
    [game]
  );

  const onAnalyze = useCallback(async () => {
    if (!id) return;
    try {
      const r = await api<AnalysisResp>(`/api/games/${id}/analyze?move=${index}`, { method: "POST" });
      setAnalysis(r);
    } catch {
      toast.error(t("errors.analysisFailed"));
    }
  }, [id, index, t]);

  // Keyboard navigation
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (!game) return;
      if ((e.target as HTMLElement)?.tagName?.match(/INPUT|TEXTAREA/)) return;
      if (e.key === "ArrowLeft") setIndex((i) => Math.max(0, i - 1));
      if (e.key === "ArrowRight") setIndex((i) => Math.min(game.moves.length, i + 1));
      if (e.key === "Home") setIndex(0);
      if (e.key === "End") setIndex(game.moves.length);
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [game]);

  if (!game) return <div className="py-6">...</div>;

  const hintOverlay = analysis
    ? analysis.top_moves.slice(0, 3).map((m, i) => {
        const xy = gtpToXy(m.move, game.board_size);
        if (!xy) return null;
        return {
          x: xy[0],
          y: xy[1],
          color: (i === 0 ? "primary" : i === 1 ? "secondary" : "tertiary") as const,
          label: String(i + 1),
        };
      }).filter((x): x is NonNullable<typeof x> => x !== null)
    : undefined;

  return (
    <div className="flex flex-col gap-6 py-4">
      <Hero
        title={t("review.title")}
        subtitle={`${new Date(game.created_at).toISOString().slice(0, 10)} · ${game.board_size}×${game.board_size} · ${game.result}`}
        size="compact"
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="flex flex-col gap-4">
          <Board size={game.board_size} board={replayedBoard} lastMove={lastMove} overlay={hintOverlay} />

          <div className="flex flex-col gap-2 border-t border-ink-faint pt-3">
            {/* Timeline scrubber */}
            <input
              type="range"
              min={0}
              max={game.moves.length}
              value={index}
              onChange={(e) => setIndex(Number(e.target.value))}
              className="w-full accent-oxblood"
              aria-label={t("review.scrubber")}
            />
            <div className="flex items-center justify-between font-mono text-xs text-ink-mute">
              <span>{index} / {game.moves.length}</span>
              <div className="flex gap-2">
                <KeybindHint keys={["←"]} description={t("review.prev")} />
                <KeybindHint keys={["→"]} description={t("review.next")} />
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setIndex(0)}>{t("review.first")}</Button>
              <Button variant="outline" size="sm" onClick={() => setIndex((i) => Math.max(0, i - 1))}>{t("review.prev")}</Button>
              <Button variant="outline" size="sm" onClick={() => setIndex((i) => Math.min(game.moves.length, i + 1))}>{t("review.next")}</Button>
              <Button variant="outline" size="sm" onClick={() => setIndex(game.moves.length)}>{t("review.last")}</Button>
              <Button size="sm" onClick={onAnalyze} className="ml-auto">{t("review.analyze")}</Button>
            </div>
          </div>
        </div>

        <aside className="flex flex-col gap-6">
          {analysis && (
            <AnalysisOverlay topMoves={analysis.top_moves} winrate={analysis.winrate} />
          )}
          <RuleDivider label={t("game.moves")} />
          <div className="max-h-[60vh] overflow-y-auto border border-ink-faint">
            <MoveList moves={moves} currentIndex={index - 1} onSelect={(i) => setIndex(i + 1)} />
          </div>
          <a
            href={`/api/games/${id}/sgf`}
            className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood hover:underline"
          >
            {t("review.downloadSgf")}
          </a>
        </aside>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add missing i18n keys**

Ensure in ko.json / en.json:
- `review.title`: "기보 복기" / "Review"
- `review.scrubber`: "수순 슬라이더" / "Move scrubber"
- `review.first`: "처음" / "First"
- `review.prev`: "이전" / "Prev"
- `review.next`: "다음" / "Next"
- `review.last`: "끝" / "Last"
- `review.analyze`: "분석" / "Analyze"
- `review.downloadSgf`: "SGF 다운로드" / "Download SGF"

- [ ] **Step 3: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/app/game/review/[id]/page.tsx web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "feat(web): Review — Editorial timeline scrubber + MoveList jump + analysis"
```

---

## Task 14 — i18n Audit Pass

**Rationale:** Tasks 1, 10, 11, 12, 13 each add keys piecemeal. This task verifies parity and no orphan keys.

**Files:**
- Modify: `web/lib/i18n/ko.json`, `en.json` (fix parity only)

- [ ] **Step 1: Check key parity**

```bash
cd web && node -e "
const ko = require('./lib/i18n/ko.json');
const en = require('./lib/i18n/en.json');
const flatten = (o, p='') => Object.entries(o).flatMap(([k,v]) => typeof v === 'object' && v !== null ? flatten(v, p+k+'.') : [[p+k, v]]);
const kf = Object.fromEntries(flatten(ko));
const ef = Object.fromEntries(flatten(en));
const inKo = Object.keys(kf), inEn = Object.keys(ef);
console.log('missing in en:', inKo.filter(k => !ef[k]));
console.log('missing in ko:', inEn.filter(k => !kf[k]));
"
```
Expected: empty arrays for both. If mismatch found, add the missing key to the deficient file.

- [ ] **Step 2: Commit (if changes)**

```bash
git add web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "chore(web/i18n): Phase 2 key parity between ko and en"
```
If no changes, skip commit.

---

## Task 15 — Playwright Visual Baseline

**Files:**
- Create: `e2e/tests/visual/phase2-baseline.spec.ts`

**Prereqs:** All screens (T10-T13) done. Dev stack running (or e2e stack via docker-compose).

- [ ] **Step 1: Add test**

Create `e2e/tests/visual/phase2-baseline.spec.ts`:
```typescript
import { test, expect, Page } from "@playwright/test";

async function setTheme(page: Page, theme: "light" | "dark") {
  await page.addInitScript((t) => {
    try { localStorage.setItem("theme", t); } catch {}
  }, theme);
}

const screens: { name: string; url: string; auth?: boolean }[] = [
  { name: "home", url: "/" },
  { name: "newgame", url: "/game/new", auth: true },
  { name: "dev-components", url: "/dev/components" },
];

for (const s of screens) {
  for (const theme of ["light", "dark"] as const) {
    test(`visual/${s.name}-${theme}`, async ({ page }) => {
      await setTheme(page, theme);
      if (s.auth) {
        // Reuse existing e2e helper that creates a test account + sets cookies.
        // If not present, skip this test (test.skip).
      }
      await page.goto(s.url);
      await page.waitForLoadState("networkidle");
      await expect(page).toHaveScreenshot(`${s.name}-${theme}.png`, {
        fullPage: true,
        maxDiffPixelRatio: 0.02,
      });
    });
  }
}
```

- [ ] **Step 2: Run to generate baselines (first run creates snapshots)**

```bash
cd e2e && npx playwright test tests/visual/phase2-baseline.spec.ts --update-snapshots
```
Expected: baseline PNGs written to `e2e/tests/visual/phase2-baseline.spec.ts-snapshots/`.

- [ ] **Step 3: Run again to verify stability**

```bash
cd e2e && npx playwright test tests/visual/phase2-baseline.spec.ts
```
Expected: all tests pass.

- [ ] **Step 4: Commit baselines**

```bash
git add e2e/tests/visual/
git commit -m "test(e2e): visual baseline snapshots for Phase 2 screens (home, newgame, catalog × day/night)"
```

---

## Task 16 — Final Verification

**Files:** none (verification only).

- [ ] **Step 1: Typecheck whole web**

```bash
cd web && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 2: Lint**

```bash
cd web && npm run lint
```
Expected: clean.

- [ ] **Step 3: Vitest**

```bash
cd web && npm test -- --run
```
Expected: all tests pass (existing + Phase 1's 28 + Phase 2 MoveList's 4 = 32+).

- [ ] **Step 4: Production build**

```bash
cd web && npm run build
```
Expected: successful. All routes build.

- [ ] **Step 5: Manual dev smoke (human verify)**

Visit each route in browser (Day + Night):
- `/` — Hero + recent games OR guest CTA
- `/game/new` — form + live summary card (logged-in only)
- `/game/play/[existing-id]` — play a few moves, pass, hint, dialog resign
- `/game/review/[existing-id]` — scrubber left/right, analyze, SGF link
- `/dev/components` — still renders (regression check)

Check:
- No console errors
- No hardcoded purple/AI-ish colors
- Keyboard shortcuts work (P/R/U/H on Play, ←/→ on Review)
- Korean + English toggle preserves page state
- Responsive: 375px mobile viewport no overflow

- [ ] **Step 6: Guardian audit**

Run grep-based audit of Phase 2 touched files:
```bash
cd /Users/daegong/projects/baduk
grep -rE '#[0-9a-fA-F]{6}' web/app/ web/components/ --include="*.tsx" | grep -v "/ui/\|globals.css" | head -10
```
Expected: no matches (except Board.tsx which uses `tokens.light[...]` via `/lib/tokens.ts` — acceptable, not hardcoded).

- [ ] **Step 7: Phase 2 complete — prepare for Phase 3**

If all verifications pass, Phase 2 is done. Next: return to `superpowers:writing-plans` to author Phase 3 (Login, Signup, History, Settings, 404).

---

## Success Criteria for Phase 2

- [ ] TopNav, Home, NewGame, Play, Review all rewritten in Editorial style
- [ ] Board, GameControls, Pickers, AnalysisOverlay use tokens and primitives
- [ ] MoveList primitive exists with 4 Vitest tests
- [ ] All WS messages and REST shapes unchanged (no backend touch)
- [ ] Keyboard shortcuts work (P/R/U/H on Play, ←/→/Home/End on Review)
- [ ] Resign flow uses Dialog confirmation
- [ ] Playwright visual baselines exist for 3+ screens × 2 themes
- [ ] Production build succeeds
- [ ] Vitest green, lint clean, tsc clean

# UI/UX 업리프트 Phase 1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install the Editorial Hardcover design system foundation (tokens, fonts, theming, 12 shadcn primitives, 10 editorial primitives, plus an internal `/dev/components` catalog page for visual verification).

**Architecture:** CSS variables in `globals.css` define light + dark token values; Tailwind maps them to utility classes; `next-themes` drives the `class` attribute for dark mode with no SSR flash. shadcn/ui primitives are copied source-first and restyled to tokens; editorial primitives are authored fresh in `components/editorial/`. All screen work (Phase 2+) builds on this foundation.

**Tech Stack:**
- Existing: Next.js 14.2.5, React 18.3, Tailwind 3.4, Zustand 4.5, Vitest 2.0
- New: Radix UI primitives (8), `next-themes` ^0.3, `sonner` ^1, `lucide-react` ^0.450, `class-variance-authority` ^0.7, `clsx` ^2, `tailwind-merge` ^2

**Out of scope (Phase 2+ plans):** TopNav, Home, New Game, Play, Review, Login/Signup, History, Settings, 404. Phase 1 leaves existing screens functionally unchanged — visual refresh starts in Phase 2.

**Scope note:** This plan is Phase 1 only. After it lands, return to `superpowers:writing-plans` with the same spec to author Phase 2 (Core Flow), Phase 3 (Peripheral), and Phase 4 (Polish) plans.

---

## File Structure — What Phase 1 Creates or Modifies

### New files
- `web/lib/cn.ts` — `clsx` + `tailwind-merge` helper used by every primitive
- `web/lib/tokens.ts` — TS constants for programmatic token access (e.g. Board SVG)
- `web/lib/fonts.ts` — `next/font/google` loaders for Newsreader, IBM Plex Sans, IBM Plex Mono
- `web/components/ui/{button,card,dialog,dropdown-menu,input,label,select,sheet,tabs,toggle-group,tooltip,separator}.tsx` — 12 shadcn primitives
- `web/components/editorial/{BrandMark,Hero,RuleDivider,StatFigure,DataBlock,PlayerCaption,KeybindHint,EmptyState,Spinner}.tsx` — 9 primitives
- `web/components/editorial/icons.tsx` — 5 Go-specific SVG icons (Pass, Resign, Undo, Hint, Handicap)
- `web/app/dev/components/page.tsx` — internal catalog page showing every primitive in both themes
- `web/tests/editorial/{stat-figure,data-block,brand-mark}.test.tsx` — unit tests for logic-bearing primitives

### Modified files
- `web/package.json` — 14 new dependencies
- `web/tailwind.config.ts` — replace minimal config with token mappings
- `web/app/globals.css` — replace 7-line reset with token CSS variables + base typography layer
- `web/app/layout.tsx` — add ThemeProvider, font variables, Sonner Toaster, Pretendard CDN link
- `web/components/TopNav.tsx` — swap `lib/theme.ts` call for `useTheme` from `next-themes` (minimal shim only; full redesign in Phase 2)

### Deleted files
- `web/components/ThemeBootstrapper.tsx` — replaced by `next-themes`
- `web/lib/theme.ts` — replaced by `useTheme()`

---

## Task 1 — Install Dependencies

**Files:**
- Modify: `web/package.json`

- [ ] **Step 1: Add dependencies via npm install**

Run from the project root:
```bash
cd web && npm install \
  @radix-ui/react-dialog@^1 \
  @radix-ui/react-dropdown-menu@^2 \
  @radix-ui/react-label@^2 \
  @radix-ui/react-select@^2 \
  @radix-ui/react-separator@^1 \
  @radix-ui/react-slot@^1 \
  @radix-ui/react-tabs@^1 \
  @radix-ui/react-toggle-group@^1 \
  @radix-ui/react-tooltip@^1 \
  class-variance-authority@^0.7 \
  clsx@^2 \
  tailwind-merge@^2 \
  lucide-react@^0.450 \
  next-themes@^0.3 \
  sonner@^1
```
Expected: no peer-dep errors. `web/package.json` + `web/package-lock.json` updated.

- [ ] **Step 2: Verify existing tests still pass**

```bash
cd web && npm test -- --run
```
Expected: all existing Vitest tests green.

- [ ] **Step 3: Verify existing app still builds**

```bash
cd web && npx tsc --noEmit
```
Expected: no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add web/package.json web/package-lock.json
git commit -m "chore(web): install design-system deps (radix, next-themes, sonner, lucide, cva)"
```

---

## Task 2 — `lib/cn.ts` Utility

**Files:**
- Create: `web/lib/cn.ts`
- Create: `web/tests/lib/cn.test.ts`

- [ ] **Step 1: Write the failing test**

Create `web/tests/lib/cn.test.ts`:
```typescript
import { describe, it, expect } from "vitest";
import { cn } from "../../lib/cn";

describe("cn", () => {
  it("merges simple class strings", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("dedupes conflicting Tailwind utilities (tailwind-merge)", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("filters falsy values", () => {
    expect(cn("a", false, null, undefined, "b")).toBe("a b");
  });

  it("handles arrays and objects (clsx)", () => {
    expect(cn(["a", "b"], { c: true, d: false })).toBe("a b c");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && npx vitest run tests/lib/cn.test.ts
```
Expected: FAIL — "Cannot find module '../../lib/cn'".

- [ ] **Step 3: Implement `cn`**

Create `web/lib/cn.ts`:
```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd web && npx vitest run tests/lib/cn.test.ts
```
Expected: 4 tests passed.

- [ ] **Step 5: Commit**

```bash
git add web/lib/cn.ts web/tests/lib/cn.test.ts
git commit -m "feat(web): add cn() class-merging utility"
```

---

## Task 3 — `lib/fonts.ts` Font Loaders

**Files:**
- Create: `web/lib/fonts.ts`

- [ ] **Step 1: Create font loader**

Create `web/lib/fonts.ts`:
```typescript
import { Newsreader, IBM_Plex_Mono } from "next/font/google";

/**
 * Pretendard loads via CDN <link> in app/layout.tsx head — not through next/font —
 * because Pretendard is not on Google Fonts. Sans stack is defined in globals.css :root.
 */
export const fontSerif = Newsreader({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-serif",
  axes: ["opsz"],
});

export const fontMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
  variable: "--font-mono",
});

export const fontVariables = [fontSerif.variable, fontMono.variable].join(" ");
```

- [ ] **Step 2: Verify typecheck**

```bash
cd web && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add web/lib/fonts.ts
git commit -m "feat(web): load Newsreader, Plex Sans, Plex Mono via next/font"
```

---

## Task 4 — `globals.css` Token CSS Variables

**Files:**
- Modify: `web/app/globals.css`

- [ ] **Step 1: Replace globals.css contents**

Overwrite `web/app/globals.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* Light — Day Edition */
    --paper: 245 239 230;
    --paper-deep: 233 223 201;
    --ink: 26 23 21;
    --ink-mute: 107 99 90;
    --ink-faint: 184 175 163;
    --oxblood: 123 30 36;
    --gold: 163 123 30;
    --moss: 46 74 58;
    --stone-black: 15 13 12;
    --stone-white: 250 245 236;

    /* Sans stack (Pretendard from CDN — not loaded via next/font) */
    --font-sans: "Pretendard Variable", Pretendard, -apple-system, system-ui, sans-serif;
  }

  .dark {
    /* Dark — Night Edition */
    --paper: 28 25 23;
    --paper-deep: 38 34 31;
    --ink: 242 235 223;
    --ink-mute: 155 146 136;
    --ink-faint: 92 84 77;
    --oxblood: 200 80 88;
    --gold: 217 166 72;
    --moss: 106 148 120;
    --stone-black: 15 13 12;
    --stone-white: 250 245 236;
  }

  html {
    font-family: var(--font-sans);
    font-feature-settings: "kern", "liga";
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  body {
    background-color: rgb(var(--paper));
    color: rgb(var(--ink));
  }

  h1, h2, h3, h4 {
    font-family: var(--font-serif), Georgia, serif;
    letter-spacing: -0.015em;
  }

  .font-display-xl { font-size: 3rem; line-height: 3.5rem; letter-spacing: -0.02em; font-weight: 600; }
  .font-display { font-size: 2rem; line-height: 2.5rem; letter-spacing: -0.02em; font-weight: 600; }
  .font-label { font-size: 0.6875rem; line-height: 1; letter-spacing: 0.16em; text-transform: uppercase; font-weight: 600; }
  .font-data-xl { font-size: 2rem; line-height: 2.25rem; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; font-weight: 500; font-family: var(--font-mono), ui-monospace, monospace; }
  .font-data { font-size: 1.25rem; line-height: 1.5rem; font-variant-numeric: tabular-nums; font-weight: 500; font-family: var(--font-mono), ui-monospace, monospace; }
  .font-data-sm { font-size: 0.8125rem; line-height: 1.125rem; font-variant-numeric: tabular-nums; font-weight: 500; font-family: var(--font-mono), ui-monospace, monospace; }
}

@layer base {
  /* Custom keyframes replacing tailwindcss-animate for Radix data-state transitions */
  @keyframes ed-fade-in { from { opacity: 0 } to { opacity: 1 } }
  @keyframes ed-fade-out { from { opacity: 1 } to { opacity: 0 } }
  @keyframes ed-slide-in-from-right { from { transform: translateX(100%) } to { transform: translateX(0) } }
  @keyframes ed-slide-out-to-right { from { transform: translateX(0) } to { transform: translateX(100%) } }

  [data-state="open"].ed-anim-fade { animation: ed-fade-in 150ms ease-out }
  [data-state="closed"].ed-anim-fade { animation: ed-fade-out 150ms ease-out }
  [data-state="open"].ed-anim-slide-right { animation: ed-slide-in-from-right 200ms ease-out }
  [data-state="closed"].ed-anim-slide-right { animation: ed-slide-out-to-right 200ms ease-out }
}

/* Pretendard CDN loads via <link> in layout.tsx */
```

- [ ] **Step 2: Verify dev server still runs**

```bash
cd web && (curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/ || echo "dev server down")
```
Expected: 200 (if dev server running) or "dev server down" (then start it; Tailwind rebuild should succeed without errors).

- [ ] **Step 3: Commit**

```bash
git add web/app/globals.css
git commit -m "feat(web): add Editorial Hardcover token CSS variables + typography layer"
```

---

## Task 5 — `tailwind.config.ts` Token Mappings

**Files:**
- Modify: `web/tailwind.config.ts`

- [ ] **Step 1: Replace tailwind.config.ts contents**

Overwrite `web/tailwind.config.ts`:
```typescript
import type { Config } from "tailwindcss";

const config: Config = {
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
        /* board.bg and board.dark kept for legacy Board.tsx until Phase 2 rewrite */
        board: { bg: "#E8C572", dark: "#C49A54" },
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans: ["var(--font-sans)"], // defined in globals.css :root
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      letterSpacing: { label: "0.16em" },
      transitionTimingFunction: { stone: "cubic-bezier(.2,.7,.2,1)" },
      transitionDuration: { stone: "300ms", page: "200ms" },
      borderRadius: { DEFAULT: "2px", sm: "2px" },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 2: Verify dev reload**

```bash
cd web && npx tsc --noEmit
```
Expected: no errors. Tailwind will regenerate utilities on next dev rebuild.

- [ ] **Step 3: Commit**

```bash
git add web/tailwind.config.ts
git commit -m "feat(web): map tokens to Tailwind utilities (paper/ink/oxblood/gold/moss)"
```

---

## Task 6 — `lib/tokens.ts` TS Constants

**Files:**
- Create: `web/lib/tokens.ts`

- [ ] **Step 1: Create token constants**

Create `web/lib/tokens.ts`:
```typescript
/**
 * Programmatic access to design tokens for places where Tailwind utilities
 * are not reachable (e.g. SVG inline attributes in Board, image generation).
 *
 * UI should prefer Tailwind classes; only use these constants when necessary.
 */

export const tokens = {
  light: {
    paper: "rgb(245 239 230)",
    "paper-deep": "rgb(233 223 201)",
    ink: "rgb(26 23 21)",
    "ink-mute": "rgb(107 99 90)",
    "ink-faint": "rgb(184 175 163)",
    oxblood: "rgb(123 30 36)",
    gold: "rgb(163 123 30)",
    moss: "rgb(46 74 58)",
    "stone-black": "rgb(15 13 12)",
    "stone-white": "rgb(250 245 236)",
  },
  dark: {
    paper: "rgb(28 25 23)",
    "paper-deep": "rgb(38 34 31)",
    ink: "rgb(242 235 223)",
    "ink-mute": "rgb(155 146 136)",
    "ink-faint": "rgb(92 84 77)",
    oxblood: "rgb(200 80 88)",
    gold: "rgb(217 166 72)",
    moss: "rgb(106 148 120)",
    "stone-black": "rgb(15 13 12)",
    "stone-white": "rgb(250 245 236)",
  },
} as const;

export const motion = {
  base: "150ms ease-out",
  stone: "300ms cubic-bezier(.2,.7,.2,1)",
  page: "200ms ease-out",
} as const;

export type TokenName = keyof typeof tokens.light;
```

- [ ] **Step 2: Verify typecheck**

```bash
cd web && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add web/lib/tokens.ts
git commit -m "feat(web): export design tokens as TS constants for programmatic use"
```

---

## Task 7 — next-themes ThemeProvider + Remove Old Theme Bootstrap

**Files:**
- Modify: `web/app/layout.tsx`
- Delete: `web/components/ThemeBootstrapper.tsx`
- Delete: `web/lib/theme.ts`
- Modify: `web/components/TopNav.tsx` — swap theme util for `useTheme()`

- [ ] **Step 1: Read current TopNav to find theme-toggle call site**

```bash
cd web && grep -n "from.*lib/theme\|ThemeBootstrapper" components/TopNav.tsx app/layout.tsx
```
Expected: identify imports referencing `@/lib/theme` or `ThemeBootstrapper`. Record line numbers for Step 4.

- [ ] **Step 2: Create new `ThemeProviderClient` wrapper**

Create `web/components/ThemeProviderClient.tsx`:
```typescript
"use client";
import { ThemeProvider } from "next-themes";
import { ReactNode } from "react";

export function ThemeProviderClient({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      {children}
    </ThemeProvider>
  );
}
```

- [ ] **Step 3: Rewrite `app/layout.tsx`**

Overwrite `web/app/layout.tsx`:
```typescript
import type { Metadata } from "next";
import "./globals.css";
import TopNav from "@/components/TopNav";
import { ThemeProviderClient } from "@/components/ThemeProviderClient";
import { fontVariables } from "@/lib/fonts";
import { Toaster } from "sonner";

export const metadata: Metadata = {
  title: "Baduk — 조용한 승부",
  description: "KataGo Human-SL과 두는 한국식 바둑 (9×9 · 13×13 · 19×19)",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" className={fontVariables} suppressHydrationWarning>
      <head>
        <link
          rel="stylesheet"
          crossOrigin="anonymous"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
        />
      </head>
      <body className="bg-paper text-ink">
        <ThemeProviderClient>
          <TopNav />
          <main className="p-4 max-w-7xl mx-auto">{children}</main>
          <Toaster position="top-center" richColors={false} closeButton />
        </ThemeProviderClient>
      </body>
    </html>
  );
}
```

- [ ] **Step 4: Update TopNav to use `useTheme()`**

In `web/components/TopNav.tsx`:
- Remove `import { ... } from "@/lib/theme"` or relative equivalent.
- Remove any `useEffect`/`localStorage` theme toggles.
- Add: `"use client";` at top if not already there.
- Add: `import { useTheme } from "next-themes";`
- Replace the existing theme toggle handler with:
  ```typescript
  const { theme, setTheme } = useTheme();
  const toggle = () => setTheme(theme === "dark" ? "light" : "dark");
  ```

(Do not redesign TopNav visually in this task — leave existing markup intact. Full TopNav redesign is Phase 2.)

- [ ] **Step 5: Delete obsolete files**

```bash
rm web/components/ThemeBootstrapper.tsx web/lib/theme.ts
```

- [ ] **Step 6: Verify typecheck + lint + dev renders**

```bash
cd web && npx tsc --noEmit && npm run lint
```
Expected: no errors. Dev server (http://localhost:3000) should render with paper/ink background; toggle should switch to dark.

- [ ] **Step 7: Commit**

```bash
git add web/app/layout.tsx web/components/ThemeProviderClient.tsx web/components/TopNav.tsx
git add -A web/components/ThemeBootstrapper.tsx web/lib/theme.ts
git commit -m "feat(web): next-themes ThemeProvider + Sonner Toaster in root layout"
```

---

## Task 8 — shadcn: Button

**Files:**
- Create: `web/components/ui/button.tsx`
- Create: `web/tests/ui/button.test.tsx`

- [ ] **Step 1: Write Button component**

Create `web/components/ui/button.tsx`:
```typescript
"use client";
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-sm font-sans text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 focus-visible:ring-offset-paper disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-ink text-paper hover:bg-ink/90",
        outline: "border border-ink text-ink hover:bg-paper-deep",
        ghost: "text-ink hover:bg-paper-deep",
        link: "text-oxblood underline-offset-4 hover:underline",
        destructive: "bg-oxblood text-paper hover:bg-oxblood/90",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-10 px-4",
        lg: "h-12 px-6 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "md" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { buttonVariants };
```

- [ ] **Step 2: Write component tests**

Create `web/tests/ui/button.test.tsx`:
```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Button } from "../../components/ui/button";

describe("Button", () => {
  it("renders with default variant", () => {
    render(<Button>Click me</Button>);
    const btn = screen.getByRole("button", { name: "Click me" });
    expect(btn).toBeInTheDocument();
    expect(btn.className).toMatch(/bg-ink/);
  });

  it("applies outline variant classes", () => {
    render(<Button variant="outline">Outline</Button>);
    expect(screen.getByRole("button").className).toMatch(/border-ink/);
  });

  it("forwards ref", () => {
    let ref: HTMLButtonElement | null = null;
    render(<Button ref={(r) => (ref = r)}>X</Button>);
    expect(ref).toBeInstanceOf(HTMLButtonElement);
  });
});
```

- [ ] **Step 3: Run tests**

```bash
cd web && npx vitest run tests/ui/button.test.tsx
```
Expected: 3 tests passed.

- [ ] **Step 4: Commit**

```bash
git add web/components/ui/button.tsx web/tests/ui/button.test.tsx
git commit -m "feat(web/ui): Button primitive with 5 variants (default/outline/ghost/link/destructive)"
```

---

## Task 9 — shadcn: Card + Separator

**Files:**
- Create: `web/components/ui/card.tsx`
- Create: `web/components/ui/separator.tsx`

- [ ] **Step 1: Write Card**

Create `web/components/ui/card.tsx`:
```typescript
import * as React from "react";
import { cn } from "@/lib/cn";

export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("border border-ink-faint bg-paper-deep", className)}
      {...props}
    />
  )
);
Card.displayName = "Card";

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("px-6 py-4 border-b border-ink-faint", className)} {...props} />
  )
);
CardHeader.displayName = "CardHeader";

export const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn("font-serif text-base font-semibold leading-6", className)} {...props} />
  )
);
CardTitle.displayName = "CardTitle";

export const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("px-6 py-4", className)} {...props} />
  )
);
CardContent.displayName = "CardContent";

export const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("px-6 py-3 border-t border-ink-faint", className)} {...props} />
  )
);
CardFooter.displayName = "CardFooter";
```

- [ ] **Step 2: Write Separator**

Create `web/components/ui/separator.tsx`:
```typescript
"use client";
import * as React from "react";
import * as SeparatorPrimitive from "@radix-ui/react-separator";
import { cn } from "@/lib/cn";

export const Separator = React.forwardRef<
  React.ElementRef<typeof SeparatorPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>
>(({ className, orientation = "horizontal", decorative = true, ...props }, ref) => (
  <SeparatorPrimitive.Root
    ref={ref}
    decorative={decorative}
    orientation={orientation}
    className={cn(
      "shrink-0 bg-ink-faint",
      orientation === "horizontal" ? "h-px w-full" : "h-full w-px",
      className
    )}
    {...props}
  />
));
Separator.displayName = "Separator";
```

- [ ] **Step 3: Typecheck**

```bash
cd web && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add web/components/ui/card.tsx web/components/ui/separator.tsx
git commit -m "feat(web/ui): Card (+Header/Title/Content/Footer) and Separator primitives"
```

---

## Task 10 — shadcn: Input + Label

**Files:**
- Create: `web/components/ui/input.tsx`
- Create: `web/components/ui/label.tsx`

- [ ] **Step 1: Write Input**

Create `web/components/ui/input.tsx`:
```typescript
import * as React from "react";
import { cn } from "@/lib/cn";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-sm border border-ink-faint bg-paper px-3 py-2 text-sm",
        "placeholder:text-ink-mute",
        "focus-visible:outline-none focus-visible:border-ink focus-visible:ring-1 focus-visible:ring-ink",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "aria-[invalid=true]:border-oxblood aria-[invalid=true]:focus-visible:ring-oxblood",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";
```

- [ ] **Step 2: Write Label**

Create `web/components/ui/label.tsx`:
```typescript
"use client";
import * as React from "react";
import * as LabelPrimitive from "@radix-ui/react-label";
import { cn } from "@/lib/cn";

export const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn(
      "font-sans text-xs font-semibold uppercase tracking-label text-ink-mute",
      "peer-disabled:opacity-50",
      className
    )}
    {...props}
  />
));
Label.displayName = "Label";
```

- [ ] **Step 3: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/ui/input.tsx web/components/ui/label.tsx
git commit -m "feat(web/ui): Input + Label primitives"
```

---

## Task 11 — shadcn: Dialog + Sheet

**Files:**
- Create: `web/components/ui/dialog.tsx`
- Create: `web/components/ui/sheet.tsx`

- [ ] **Step 1: Write Dialog**

Create `web/components/ui/dialog.tsx`:
```typescript
"use client";
import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogPortal = DialogPrimitive.Portal;
export const DialogClose = DialogPrimitive.Close;

export const DialogOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn("fixed inset-0 z-50 bg-ink/50 ed-anim-fade", className)}
    {...props}
  />
));
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName;

export const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border border-ink bg-paper p-6 ed-anim-fade",
        className
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close className="absolute right-4 top-4 text-ink-mute hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink">
        <X size={16} strokeWidth={1.5} />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPortal>
));
DialogContent.displayName = DialogPrimitive.Content.displayName;

export const DialogHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col gap-1.5 border-b border-ink-faint pb-3", className)} {...props} />
);

export const DialogTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn("font-serif text-xl font-semibold leading-7", className)}
    {...props}
  />
));
DialogTitle.displayName = DialogPrimitive.Title.displayName;

export const DialogDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn("text-sm text-ink-mute", className)}
    {...props}
  />
));
DialogDescription.displayName = DialogPrimitive.Description.displayName;
```

- [ ] **Step 2: Write Sheet**

Create `web/components/ui/sheet.tsx`:
```typescript
"use client";
import * as React from "react";
import * as SheetPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

export const Sheet = SheetPrimitive.Root;
export const SheetTrigger = SheetPrimitive.Trigger;
export const SheetClose = SheetPrimitive.Close;
export const SheetPortal = SheetPrimitive.Portal;

export const SheetOverlay = React.forwardRef<
  React.ElementRef<typeof SheetPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof SheetPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <SheetPrimitive.Overlay
    ref={ref}
    className={cn("fixed inset-0 z-50 bg-ink/50 ed-anim-fade", className)}
    {...props}
  />
));
SheetOverlay.displayName = SheetPrimitive.Overlay.displayName;

const sheetVariants = cva(
  "fixed z-50 gap-4 bg-paper p-6 border-ink-faint",
  {
    variants: {
      side: {
        top: "inset-x-0 top-0 border-b",
        bottom: "inset-x-0 bottom-0 border-t",
        left: "inset-y-0 left-0 h-full w-3/4 max-w-sm border-r",
        right: "inset-y-0 right-0 h-full w-3/4 max-w-sm border-l ed-anim-slide-right",
      },
    },
    defaultVariants: { side: "right" },
  }
);

interface SheetContentProps
  extends React.ComponentPropsWithoutRef<typeof SheetPrimitive.Content>,
    VariantProps<typeof sheetVariants> {}

export const SheetContent = React.forwardRef<
  React.ElementRef<typeof SheetPrimitive.Content>,
  SheetContentProps
>(({ side = "right", className, children, ...props }, ref) => (
  <SheetPortal>
    <SheetOverlay />
    <SheetPrimitive.Content
      ref={ref}
      className={cn(sheetVariants({ side }), className)}
      {...props}
    >
      {children}
      <SheetPrimitive.Close className="absolute right-4 top-4 text-ink-mute hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink">
        <X size={16} strokeWidth={1.5} />
        <span className="sr-only">Close</span>
      </SheetPrimitive.Close>
    </SheetPrimitive.Content>
  </SheetPortal>
));
SheetContent.displayName = SheetPrimitive.Content.displayName;
```

- [ ] **Step 3: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/ui/dialog.tsx web/components/ui/sheet.tsx
git commit -m "feat(web/ui): Dialog + Sheet primitives (Radix Dialog-based)"
```

---

## Task 12 — shadcn: DropdownMenu

**Files:**
- Create: `web/components/ui/dropdown-menu.tsx`

- [ ] **Step 1: Write DropdownMenu**

Create `web/components/ui/dropdown-menu.tsx`:
```typescript
"use client";
import * as React from "react";
import * as DMPrimitive from "@radix-ui/react-dropdown-menu";
import { cn } from "@/lib/cn";

export const DropdownMenu = DMPrimitive.Root;
export const DropdownMenuTrigger = DMPrimitive.Trigger;
export const DropdownMenuGroup = DMPrimitive.Group;
export const DropdownMenuPortal = DMPrimitive.Portal;
export const DropdownMenuSub = DMPrimitive.Sub;
export const DropdownMenuRadioGroup = DMPrimitive.RadioGroup;

export const DropdownMenuContent = React.forwardRef<
  React.ElementRef<typeof DMPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DMPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <DMPrimitive.Portal>
    <DMPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        "z-50 min-w-[8rem] overflow-hidden border border-ink-faint bg-paper p-1 text-ink ed-anim-fade",
        className
      )}
      {...props}
    />
  </DMPrimitive.Portal>
));
DropdownMenuContent.displayName = DMPrimitive.Content.displayName;

export const DropdownMenuItem = React.forwardRef<
  React.ElementRef<typeof DMPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof DMPrimitive.Item> & { inset?: boolean }
>(({ className, inset, ...props }, ref) => (
  <DMPrimitive.Item
    ref={ref}
    className={cn(
      "relative flex cursor-default select-none items-center gap-2 px-3 py-2 text-sm outline-none",
      "focus:bg-paper-deep data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
      inset && "pl-8",
      className
    )}
    {...props}
  />
));
DropdownMenuItem.displayName = DMPrimitive.Item.displayName;

export const DropdownMenuSeparator = React.forwardRef<
  React.ElementRef<typeof DMPrimitive.Separator>,
  React.ComponentPropsWithoutRef<typeof DMPrimitive.Separator>
>(({ className, ...props }, ref) => (
  <DMPrimitive.Separator
    ref={ref}
    className={cn("-mx-1 my-1 h-px bg-ink-faint", className)}
    {...props}
  />
));
DropdownMenuSeparator.displayName = DMPrimitive.Separator.displayName;

export const DropdownMenuLabel = React.forwardRef<
  React.ElementRef<typeof DMPrimitive.Label>,
  React.ComponentPropsWithoutRef<typeof DMPrimitive.Label>
>(({ className, ...props }, ref) => (
  <DMPrimitive.Label
    ref={ref}
    className={cn("px-3 py-1.5 font-sans text-xs font-semibold uppercase tracking-label text-ink-mute", className)}
    {...props}
  />
));
DropdownMenuLabel.displayName = DMPrimitive.Label.displayName;
```

- [ ] **Step 2: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/ui/dropdown-menu.tsx
git commit -m "feat(web/ui): DropdownMenu primitive"
```

---

## Task 13 — shadcn: Select

**Files:**
- Create: `web/components/ui/select.tsx`

- [ ] **Step 1: Write Select**

Create `web/components/ui/select.tsx`:
```typescript
"use client";
import * as React from "react";
import * as SelectPrimitive from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";

export const Select = SelectPrimitive.Root;
export const SelectGroup = SelectPrimitive.Group;
export const SelectValue = SelectPrimitive.Value;

export const SelectTrigger = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Trigger
    ref={ref}
    className={cn(
      "flex h-10 w-full items-center justify-between rounded-sm border border-ink-faint bg-paper px-3 py-2 text-sm",
      "placeholder:text-ink-mute",
      "focus-visible:outline-none focus-visible:border-ink focus-visible:ring-1 focus-visible:ring-ink",
      "disabled:cursor-not-allowed disabled:opacity-50",
      className
    )}
    {...props}
  >
    {children}
    <SelectPrimitive.Icon asChild>
      <ChevronDown size={16} strokeWidth={1.5} className="text-ink-mute" />
    </SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>
));
SelectTrigger.displayName = SelectPrimitive.Trigger.displayName;

export const SelectContent = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>
>(({ className, children, position = "popper", ...props }, ref) => (
  <SelectPrimitive.Portal>
    <SelectPrimitive.Content
      ref={ref}
      position={position}
      className={cn(
        "relative z-50 min-w-[8rem] overflow-hidden border border-ink-faint bg-paper text-ink ed-anim-fade",
        position === "popper" && "data-[side=bottom]:translate-y-1 data-[side=top]:-translate-y-1",
        className
      )}
      {...props}
    >
      <SelectPrimitive.Viewport className={cn("p-1", position === "popper" && "w-full min-w-[var(--radix-select-trigger-width)]")}>
        {children}
      </SelectPrimitive.Viewport>
    </SelectPrimitive.Content>
  </SelectPrimitive.Portal>
));
SelectContent.displayName = SelectPrimitive.Content.displayName;

export const SelectItem = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={cn(
      "relative flex w-full cursor-default select-none items-center py-2 pl-8 pr-2 text-sm outline-none",
      "focus:bg-paper-deep data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
      className
    )}
    {...props}
  >
    <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
      <SelectPrimitive.ItemIndicator>
        <Check size={14} strokeWidth={1.5} />
      </SelectPrimitive.ItemIndicator>
    </span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
));
SelectItem.displayName = SelectPrimitive.Item.displayName;
```

- [ ] **Step 2: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/ui/select.tsx
git commit -m "feat(web/ui): Select primitive"
```

---

## Task 14 — shadcn: Tabs + ToggleGroup

**Files:**
- Create: `web/components/ui/tabs.tsx`
- Create: `web/components/ui/toggle-group.tsx`

- [ ] **Step 1: Write Tabs**

Create `web/components/ui/tabs.tsx`:
```typescript
"use client";
import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/cn";

export const Tabs = TabsPrimitive.Root;

export const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn("inline-flex gap-6 border-b border-ink-faint", className)}
    {...props}
  />
));
TabsList.displayName = TabsPrimitive.List.displayName;

export const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "-mb-px border-b-2 border-transparent py-2 text-sm text-ink-mute",
      "data-[state=active]:border-ink data-[state=active]:text-ink",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink",
      className
    )}
    {...props}
  />
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

export const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content ref={ref} className={cn("mt-4", className)} {...props} />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;
```

- [ ] **Step 2: Write ToggleGroup**

Create `web/components/ui/toggle-group.tsx`:
```typescript
"use client";
import * as React from "react";
import * as TGPrimitive from "@radix-ui/react-toggle-group";
import { cn } from "@/lib/cn";

export const ToggleGroup = React.forwardRef<
  React.ElementRef<typeof TGPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof TGPrimitive.Root>
>(({ className, ...props }, ref) => (
  <TGPrimitive.Root
    ref={ref}
    className={cn("inline-flex border border-ink-faint divide-x divide-ink-faint", className)}
    {...props}
  />
));
ToggleGroup.displayName = TGPrimitive.Root.displayName;

export const ToggleGroupItem = React.forwardRef<
  React.ElementRef<typeof TGPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof TGPrimitive.Item>
>(({ className, ...props }, ref) => (
  <TGPrimitive.Item
    ref={ref}
    className={cn(
      "inline-flex h-9 items-center justify-center gap-1 bg-paper px-3 text-xs font-semibold uppercase tracking-label text-ink-mute",
      "hover:bg-paper-deep",
      "data-[state=on]:bg-ink data-[state=on]:text-paper",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-inset",
      className
    )}
    {...props}
  />
));
ToggleGroupItem.displayName = TGPrimitive.Item.displayName;
```

- [ ] **Step 3: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/ui/tabs.tsx web/components/ui/toggle-group.tsx
git commit -m "feat(web/ui): Tabs + ToggleGroup primitives"
```

---

## Task 15 — shadcn: Tooltip

**Files:**
- Create: `web/components/ui/tooltip.tsx`

- [ ] **Step 1: Write Tooltip**

Create `web/components/ui/tooltip.tsx`:
```typescript
"use client";
import * as React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cn } from "@/lib/cn";

export const TooltipProvider = TooltipPrimitive.Provider;
export const Tooltip = TooltipPrimitive.Root;
export const TooltipTrigger = TooltipPrimitive.Trigger;

export const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Content
    ref={ref}
    sideOffset={sideOffset}
    className={cn(
      "z-50 overflow-hidden bg-ink px-2 py-1 font-mono text-xs text-paper ed-anim-fade",
      className
    )}
    {...props}
  />
));
TooltipContent.displayName = TooltipPrimitive.Content.displayName;
```

- [ ] **Step 2: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/ui/tooltip.tsx
git commit -m "feat(web/ui): Tooltip primitive"
```

---

## Task 16 — Editorial: BrandMark

**Files:**
- Create: `web/components/editorial/BrandMark.tsx`
- Create: `web/tests/editorial/brand-mark.test.tsx`

- [ ] **Step 1: Write BrandMark**

Create `web/components/editorial/BrandMark.tsx`:
```typescript
import * as React from "react";
import { cn } from "@/lib/cn";

export interface BrandMarkProps extends React.SVGAttributes<SVGSVGElement> {
  size?: 16 | 20 | 24 | 32;
}

/**
 * A single stone intersecting a horizontal grid line — the moment of a move.
 * Uses currentColor so it inherits text color (text-ink etc).
 */
export const BrandMark = React.forwardRef<SVGSVGElement, BrandMarkProps>(
  ({ size = 20, className, ...props }, ref) => (
    <svg
      ref={ref}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={cn("text-ink", className)}
      role="img"
      aria-label="Baduk"
      {...props}
    >
      <line x1="2" y1="12" x2="22" y2="12" stroke="currentColor" strokeWidth="1" />
      <circle cx="12" cy="12" r="5.5" fill="currentColor" />
    </svg>
  )
);
BrandMark.displayName = "BrandMark";
```

- [ ] **Step 2: Write test**

Create `web/tests/editorial/brand-mark.test.tsx`:
```typescript
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { BrandMark } from "../../components/editorial/BrandMark";

describe("BrandMark", () => {
  it("renders an SVG with aria-label", () => {
    const { container } = render(<BrandMark />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("aria-label", "Baduk");
    expect(svg).toHaveAttribute("width", "20");
  });

  it("accepts custom size", () => {
    const { container } = render(<BrandMark size={32} />);
    expect(container.querySelector("svg")).toHaveAttribute("width", "32");
  });
});
```

- [ ] **Step 3: Run test + commit**

```bash
cd web && npx vitest run tests/editorial/brand-mark.test.tsx
git add web/components/editorial/BrandMark.tsx web/tests/editorial/brand-mark.test.tsx
git commit -m "feat(web/editorial): BrandMark SVG (stone × gridline)"
```

---

## Task 17 — Editorial: RuleDivider

**Files:**
- Create: `web/components/editorial/RuleDivider.tsx`

- [ ] **Step 1: Write RuleDivider**

Create `web/components/editorial/RuleDivider.tsx`:
```typescript
import * as React from "react";
import { cn } from "@/lib/cn";

export interface RuleDividerProps extends React.HTMLAttributes<HTMLDivElement> {
  weight?: "faint" | "strong";
  label?: string;
}

/**
 * Editorial rule line. Horizontal only. Optional centered uppercase label
 * bisects the line (like magazine section markers).
 */
export const RuleDivider = React.forwardRef<HTMLDivElement, RuleDividerProps>(
  ({ weight = "faint", label, className, ...props }, ref) => {
    const borderColor = weight === "strong" ? "border-ink" : "border-ink-faint";
    if (!label) {
      return (
        <div
          ref={ref}
          role="separator"
          className={cn("h-px w-full border-t", borderColor, className)}
          {...props}
        />
      );
    }
    return (
      <div
        ref={ref}
        role="separator"
        aria-label={label}
        className={cn("flex items-center gap-3 w-full", className)}
        {...props}
      >
        <div className={cn("h-px flex-1 border-t", borderColor)} />
        <span className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
          {label}
        </span>
        <div className={cn("h-px flex-1 border-t", borderColor)} />
      </div>
    );
  }
);
RuleDivider.displayName = "RuleDivider";
```

- [ ] **Step 2: Commit**

```bash
cd web && npx tsc --noEmit
git add web/components/editorial/RuleDivider.tsx
git commit -m "feat(web/editorial): RuleDivider with optional section label"
```

---

## Task 18 — Editorial: Hero

**Files:**
- Create: `web/components/editorial/Hero.tsx`

- [ ] **Step 1: Write Hero**

Create `web/components/editorial/Hero.tsx`:
```typescript
import * as React from "react";
import { cn } from "@/lib/cn";
import { RuleDivider } from "./RuleDivider";

export interface HeroProps extends React.HTMLAttributes<HTMLElement> {
  title: string;
  subtitle?: string;
  volume?: string;
  size?: "default" | "compact";
}

export const Hero = React.forwardRef<HTMLElement, HeroProps>(
  ({ title, subtitle, volume, size = "default", className, ...props }, ref) => {
    const titleClass = size === "compact"
      ? "font-serif text-3xl font-semibold leading-tight tracking-tight"
      : "font-serif text-5xl font-semibold leading-tight tracking-tight";
    return (
      <section ref={ref} className={cn("flex flex-col gap-3", className)} {...props}>
        {volume && (
          <div className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood">
            {volume}
          </div>
        )}
        <h1 className={titleClass}>{title}</h1>
        {subtitle && (
          <p className="font-sans text-base text-ink-mute max-w-prose">{subtitle}</p>
        )}
        <RuleDivider weight="strong" className="mt-2" />
      </section>
    );
  }
);
Hero.displayName = "Hero";
```

- [ ] **Step 2: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/editorial/Hero.tsx
git commit -m "feat(web/editorial): Hero (volume label + serif title + rule divider)"
```

---

## Task 19 — Editorial: StatFigure

**Files:**
- Create: `web/components/editorial/StatFigure.tsx`
- Create: `web/tests/editorial/stat-figure.test.tsx`

- [ ] **Step 1: Write failing test**

Create `web/tests/editorial/stat-figure.test.tsx`:
```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatFigure } from "../../components/editorial/StatFigure";

describe("StatFigure", () => {
  it("renders value with label", () => {
    render(<StatFigure value="62.3" unit="%" label="Win Rate" />);
    expect(screen.getByText("Win Rate")).toBeInTheDocument();
    expect(screen.getByText("62.3")).toBeInTheDocument();
    expect(screen.getByText("%")).toBeInTheDocument();
  });

  it("applies tabular-nums to value element", () => {
    const { container } = render(<StatFigure value="47" label="Move" />);
    const val = container.querySelector("[data-stat-value]");
    expect(val?.className).toMatch(/font-mono/);
  });

  it("accepts numeric value and formats as string", () => {
    render(<StatFigure value={100} label="Score" />);
    expect(screen.getByText("100")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && npx vitest run tests/editorial/stat-figure.test.tsx
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement StatFigure**

Create `web/components/editorial/StatFigure.tsx`:
```typescript
import * as React from "react";
import { cn } from "@/lib/cn";

export interface StatFigureProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string | number;
  unit?: string;
  label: string;
  trend?: "up" | "down" | null;
}

export const StatFigure = React.forwardRef<HTMLDivElement, StatFigureProps>(
  ({ value, unit, label, trend, className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-1", className)} {...props}>
      <div className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
        {label}
      </div>
      <div className="flex items-baseline gap-1">
        <span
          data-stat-value
          className="font-mono text-4xl font-medium leading-none tracking-tight tabular-nums text-ink"
        >
          {typeof value === "number" ? value.toString() : value}
        </span>
        {unit && <span className="font-mono text-sm text-ink-mute">{unit}</span>}
        {trend === "up" && <span className="text-moss ml-1" aria-label="up">▲</span>}
        {trend === "down" && <span className="text-oxblood ml-1" aria-label="down">▼</span>}
      </div>
    </div>
  )
);
StatFigure.displayName = "StatFigure";
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd web && npx vitest run tests/editorial/stat-figure.test.tsx
```
Expected: 3 tests passed.

- [ ] **Step 5: Commit**

```bash
git add web/components/editorial/StatFigure.tsx web/tests/editorial/stat-figure.test.tsx
git commit -m "feat(web/editorial): StatFigure (big tabular number + label + trend)"
```

---

## Task 20 — Editorial: DataBlock

**Files:**
- Create: `web/components/editorial/DataBlock.tsx`
- Create: `web/tests/editorial/data-block.test.tsx`

- [ ] **Step 1: Write failing test**

Create `web/tests/editorial/data-block.test.tsx`:
```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DataBlock } from "../../components/editorial/DataBlock";

describe("DataBlock", () => {
  it("renders label and value", () => {
    render(<DataBlock label="Move" value="47" />);
    expect(screen.getByText("Move")).toBeInTheDocument();
    expect(screen.getByText("47")).toBeInTheDocument();
  });

  it("renders optional description", () => {
    render(<DataBlock label="Time" value="4:22" description="left on clock" />);
    expect(screen.getByText("left on clock")).toBeInTheDocument();
  });

  it("accepts ReactNode as value for compound displays", () => {
    render(<DataBlock label="Capture" value={<span>● 3 ○ 2</span>} />);
    expect(screen.getByText("● 3 ○ 2")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test (should fail)**

```bash
cd web && npx vitest run tests/editorial/data-block.test.tsx
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement DataBlock**

Create `web/components/editorial/DataBlock.tsx`:
```typescript
import * as React from "react";
import { cn } from "@/lib/cn";

export interface DataBlockProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  value: React.ReactNode;
  description?: string;
}

export const DataBlock = React.forwardRef<HTMLDivElement, DataBlockProps>(
  ({ label, value, description, className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-0.5 py-2", className)} {...props}>
      <div className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
        {label}
      </div>
      <div className="font-mono text-lg font-medium tabular-nums text-ink">
        {value}
      </div>
      {description && (
        <div className="font-sans text-xs text-ink-mute">{description}</div>
      )}
    </div>
  )
);
DataBlock.displayName = "DataBlock";
```

- [ ] **Step 4: Run test (should pass) + commit**

```bash
cd web && npx vitest run tests/editorial/data-block.test.tsx
git add web/components/editorial/DataBlock.tsx web/tests/editorial/data-block.test.tsx
git commit -m "feat(web/editorial): DataBlock (label + mono value + optional description)"
```

---

## Task 21 — Editorial: PlayerCaption

**Files:**
- Create: `web/components/editorial/PlayerCaption.tsx`

- [ ] **Step 1: Write PlayerCaption**

Create `web/components/editorial/PlayerCaption.tsx`:
```typescript
import * as React from "react";
import { cn } from "@/lib/cn";

export interface PlayerCaptionProps extends React.HTMLAttributes<HTMLDivElement> {
  name: string;
  rank?: string;
  color: "black" | "white";
  subtitle?: string;
}

export const PlayerCaption = React.forwardRef<HTMLDivElement, PlayerCaptionProps>(
  ({ name, rank, color, subtitle, className, ...props }, ref) => {
    const stoneClass = color === "black"
      ? "bg-stone-black border-stone-black"
      : "bg-stone-white border-ink";
    return (
      <div ref={ref} className={cn("flex items-center gap-3", className)} {...props}>
        <span
          aria-hidden
          className={cn("h-4 w-4 rounded-full border", stoneClass)}
        />
        <div className="flex flex-col gap-0.5">
          <div className="flex items-baseline gap-2">
            <span className="font-sans text-sm font-semibold text-ink">{name}</span>
            {rank && <span className="font-mono text-xs text-ink-mute">{rank}</span>}
          </div>
          {subtitle && (
            <span className="font-sans text-xs text-ink-mute">{subtitle}</span>
          )}
        </div>
      </div>
    );
  }
);
PlayerCaption.displayName = "PlayerCaption";
```

- [ ] **Step 2: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/editorial/PlayerCaption.tsx
git commit -m "feat(web/editorial): PlayerCaption (stone indicator + name + rank)"
```

---

## Task 22 — Editorial: KeybindHint

**Files:**
- Create: `web/components/editorial/KeybindHint.tsx`

- [ ] **Step 1: Write KeybindHint**

Create `web/components/editorial/KeybindHint.tsx`:
```typescript
import * as React from "react";
import { cn } from "@/lib/cn";

export interface KeybindHintProps extends React.HTMLAttributes<HTMLSpanElement> {
  keys: string[]; // e.g. ["P"] or ["⌘", "K"]
  description?: string;
}

export const KeybindHint = React.forwardRef<HTMLSpanElement, KeybindHintProps>(
  ({ keys, description, className, ...props }, ref) => (
    <span
      ref={ref}
      className={cn("inline-flex items-center gap-1.5 font-sans text-xs text-ink-mute", className)}
      {...props}
    >
      {keys.map((k, i) => (
        <kbd
          key={`${k}-${i}`}
          className="inline-flex h-5 min-w-[1.25rem] items-center justify-center border border-ink-faint bg-paper px-1 font-mono text-[10px] font-medium text-ink"
        >
          {k}
        </kbd>
      ))}
      {description && <span className="ml-1">{description}</span>}
    </span>
  )
);
KeybindHint.displayName = "KeybindHint";
```

- [ ] **Step 2: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/editorial/KeybindHint.tsx
git commit -m "feat(web/editorial): KeybindHint (<kbd> shortcut display)"
```

---

## Task 23 — Editorial: EmptyState

**Files:**
- Create: `web/components/editorial/EmptyState.tsx`

- [ ] **Step 1: Write EmptyState**

Create `web/components/editorial/EmptyState.tsx`:
```typescript
import * as React from "react";
import { cn } from "@/lib/cn";

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export const EmptyState = React.forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ icon, title, description, action, className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "flex flex-col items-center justify-center gap-4 border border-ink-faint bg-paper-deep px-8 py-16 text-center",
        className
      )}
      {...props}
    >
      {icon && <div className="text-ink-mute">{icon}</div>}
      <div className="flex flex-col gap-2">
        <h3 className="font-serif text-xl font-semibold text-ink">{title}</h3>
        {description && (
          <p className="font-sans text-sm text-ink-mute max-w-md">{description}</p>
        )}
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
);
EmptyState.displayName = "EmptyState";
```

- [ ] **Step 2: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/editorial/EmptyState.tsx
git commit -m "feat(web/editorial): EmptyState (icon + title + description + action)"
```

---

## Task 24 — Editorial: Spinner

**Files:**
- Create: `web/components/editorial/Spinner.tsx`
- Modify: `web/app/globals.css` (add keyframes)

- [ ] **Step 1: Add keyframes to globals.css**

In `web/app/globals.css`, append inside the last `@layer base {}` block:
```css
  @keyframes ed-linear-slide {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }
  .ed-spinner-bar {
    animation: ed-linear-slide 1.2s linear infinite;
  }
```

- [ ] **Step 2: Write Spinner**

Create `web/components/editorial/Spinner.tsx`:
```typescript
import * as React from "react";
import { cn } from "@/lib/cn";

export interface SpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: "sm" | "md";
  label?: string;
}

export const Spinner = React.forwardRef<HTMLDivElement, SpinnerProps>(
  ({ size = "md", label = "Loading", className, ...props }, ref) => {
    const h = size === "sm" ? "h-0.5" : "h-1";
    return (
      <div
        ref={ref}
        role="status"
        aria-label={label}
        className={cn("relative w-full overflow-hidden bg-ink-faint/30", h, className)}
        {...props}
      >
        <div className={cn("absolute inset-y-0 w-1/3 bg-oxblood ed-spinner-bar")} />
      </div>
    );
  }
);
Spinner.displayName = "Spinner";
```

- [ ] **Step 3: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/editorial/Spinner.tsx web/app/globals.css
git commit -m "feat(web/editorial): Spinner (linear indeterminate oxblood bar)"
```

---

## Task 25 — Editorial: Go-specific Icons

**Files:**
- Create: `web/components/editorial/icons.tsx`

- [ ] **Step 1: Write icon set**

Create `web/components/editorial/icons.tsx`:
```typescript
import * as React from "react";

type IconProps = React.SVGAttributes<SVGSVGElement> & { size?: number };

const svgBase = (size: number): React.SVGAttributes<SVGSVGElement> => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
});

export const IconPass = ({ size = 16, ...props }: IconProps) => (
  <svg {...svgBase(size)} aria-hidden="true" {...props}>
    <line x1="5" y1="19" x2="19" y2="5" />
    <circle cx="8" cy="16" r="1.5" fill="currentColor" />
  </svg>
);

export const IconResign = ({ size = 16, ...props }: IconProps) => (
  <svg {...svgBase(size)} aria-hidden="true" {...props}>
    <circle cx="12" cy="12" r="9" />
    <line x1="12" y1="3" x2="12" y2="21" />
  </svg>
);

export const IconUndo = ({ size = 16, ...props }: IconProps) => (
  <svg {...svgBase(size)} aria-hidden="true" {...props}>
    <path d="M9 14L4 9l5-5" />
    <path d="M4 9h10a6 6 0 010 12h-3" />
  </svg>
);

export const IconHint = ({ size = 16, ...props }: IconProps) => (
  <svg {...svgBase(size)} aria-hidden="true" {...props}>
    <circle cx="12" cy="12" r="9" />
    <circle cx="12" cy="12" r="3" fill="currentColor" />
  </svg>
);

export const IconHandicap = ({ size = 16, ...props }: IconProps) => (
  <svg {...svgBase(size)} aria-hidden="true" {...props}>
    <circle cx="7" cy="7" r="1.5" fill="currentColor" />
    <circle cx="17" cy="7" r="1.5" fill="currentColor" />
    <circle cx="7" cy="17" r="1.5" fill="currentColor" />
    <circle cx="17" cy="17" r="1.5" fill="currentColor" />
    <circle cx="12" cy="12" r="1.5" fill="currentColor" />
  </svg>
);
```

- [ ] **Step 2: Typecheck + commit**

```bash
cd web && npx tsc --noEmit
git add web/components/editorial/icons.tsx
git commit -m "feat(web/editorial): Go-specific icons (Pass/Resign/Undo/Hint/Handicap)"
```

---

## Task 26 — `/dev/components` Catalog Page

**Files:**
- Create: `web/app/dev/components/page.tsx`

- [ ] **Step 1: Write the catalog page**

Create `web/app/dev/components/page.tsx`:
```typescript
"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "@/components/ui/select";
import { Sheet, SheetTrigger, SheetContent } from "@/components/ui/sheet";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { BrandMark } from "@/components/editorial/BrandMark";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { StatFigure } from "@/components/editorial/StatFigure";
import { DataBlock } from "@/components/editorial/DataBlock";
import { PlayerCaption } from "@/components/editorial/PlayerCaption";
import { KeybindHint } from "@/components/editorial/KeybindHint";
import { EmptyState } from "@/components/editorial/EmptyState";
import { Spinner } from "@/components/editorial/Spinner";
import { IconPass, IconResign, IconUndo, IconHint, IconHandicap } from "@/components/editorial/icons";
import { toast } from "sonner";
import { useTheme } from "next-themes";

export default function ComponentsCatalog() {
  const { theme, setTheme } = useTheme();
  const [togglePosition, setTogglePosition] = useState("light");

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <section className="flex flex-col gap-4 py-8">
      <RuleDivider label={title} weight="strong" />
      <div className="flex flex-wrap items-start gap-6">{children}</div>
    </section>
  );

  return (
    <TooltipProvider>
      <div className="flex flex-col gap-6 pb-16">
        <Hero
          title="Component Catalog"
          subtitle="Internal visual smoke test for the Editorial Hardcover design system."
          volume="DEV"
        />

        <div className="flex gap-3">
          <Button onClick={() => setTheme("light")} variant={theme === "light" ? "default" : "outline"} size="sm">Day</Button>
          <Button onClick={() => setTheme("dark")} variant={theme === "dark" ? "default" : "outline"} size="sm">Night</Button>
          <Button onClick={() => setTheme("system")} variant={theme === "system" ? "default" : "outline"} size="sm">System</Button>
        </div>

        <Section title="Buttons">
          <Button>Default</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="link">Link</Button>
          <Button variant="destructive">Destructive</Button>
          <Button size="sm">Small</Button>
          <Button size="lg">Large</Button>
          <Button disabled>Disabled</Button>
        </Section>

        <Section title="BrandMark">
          <BrandMark size={16} />
          <BrandMark size={20} />
          <BrandMark size={24} />
          <BrandMark size={32} />
        </Section>

        <Section title="Stats & Data">
          <StatFigure value="62.3" unit="%" label="Win Rate" trend="up" />
          <StatFigure value={47} label="Move" />
          <StatFigure value="04:22" label="Time" />
          <DataBlock label="Captures" value="● 3  ○ 2" />
          <DataBlock label="Board" value="9 × 9" description="Komi 6.5" />
        </Section>

        <Section title="Players">
          <PlayerCaption color="black" name="rarebirds" rank="1단" subtitle="0:21 used" />
          <PlayerCaption color="white" name="KataGo" rank="Human-SL 3d" subtitle="thinking..." />
        </Section>

        <Section title="Inputs">
          <div className="flex flex-col gap-2 w-64">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" placeholder="you@example.com" />
          </div>
          <div className="flex flex-col gap-2 w-64">
            <Label htmlFor="err">Invalid field</Label>
            <Input id="err" aria-invalid="true" defaultValue="…" />
          </div>
        </Section>

        <Section title="Select">
          <Select>
            <SelectTrigger className="w-60"><SelectValue placeholder="Board size" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="9">9 × 9</SelectItem>
              <SelectItem value="13">13 × 13</SelectItem>
              <SelectItem value="19">19 × 19</SelectItem>
            </SelectContent>
          </Select>
        </Section>

        <Section title="Dialog & Sheet">
          <Dialog>
            <DialogTrigger asChild><Button variant="outline">Open Dialog</Button></DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>기권하시겠습니까?</DialogTitle>
                <DialogDescription>현재 대국을 기권으로 종료합니다. 기보는 저장됩니다.</DialogDescription>
              </DialogHeader>
              <div className="flex gap-2 justify-end">
                <Button variant="ghost">취소</Button>
                <Button variant="destructive">기권</Button>
              </div>
            </DialogContent>
          </Dialog>
          <Sheet>
            <SheetTrigger asChild><Button variant="outline">Open Sheet</Button></SheetTrigger>
            <SheetContent side="right">
              <h3 className="font-serif text-xl font-semibold mb-4">Analysis</h3>
              <StatFigure value="62.3" unit="%" label="Win Rate" trend="up" />
            </SheetContent>
          </Sheet>
        </Section>

        <Section title="DropdownMenu">
          <DropdownMenu>
            <DropdownMenuTrigger asChild><Button variant="ghost">User</Button></DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuLabel>Account</DropdownMenuLabel>
              <DropdownMenuItem>Profile</DropdownMenuItem>
              <DropdownMenuItem>Games</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem>Logout</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </Section>

        <Section title="Tabs & ToggleGroup">
          <Tabs defaultValue="play" className="w-[400px]">
            <TabsList>
              <TabsTrigger value="play">Play</TabsTrigger>
              <TabsTrigger value="review">Review</TabsTrigger>
              <TabsTrigger value="history">History</TabsTrigger>
            </TabsList>
            <TabsContent value="play">Play content</TabsContent>
            <TabsContent value="review">Review content</TabsContent>
            <TabsContent value="history">History content</TabsContent>
          </Tabs>
          <ToggleGroup type="single" value={togglePosition} onValueChange={(v) => v && setTogglePosition(v)}>
            <ToggleGroupItem value="light">Day</ToggleGroupItem>
            <ToggleGroupItem value="dark">Night</ToggleGroupItem>
            <ToggleGroupItem value="system">System</ToggleGroupItem>
          </ToggleGroup>
        </Section>

        <Section title="Tooltip + Keybinds">
          <Tooltip>
            <TooltipTrigger asChild><Button variant="outline">Hover me</Button></TooltipTrigger>
            <TooltipContent>Press Enter</TooltipContent>
          </Tooltip>
          <KeybindHint keys={["P"]} description="Pass" />
          <KeybindHint keys={["⌘", "K"]} description="Command" />
        </Section>

        <Section title="Icons">
          <IconPass /> <IconResign /> <IconUndo /> <IconHint /> <IconHandicap />
        </Section>

        <Section title="Toast">
          <Button onClick={() => toast("착수 완료 — E4")}>Trigger toast</Button>
          <Button onClick={() => toast.error("연결이 끊겼습니다.")} variant="destructive">Error toast</Button>
        </Section>

        <Section title="Spinner">
          <div className="w-64"><Spinner /></div>
          <div className="w-64"><Spinner size="sm" /></div>
        </Section>

        <Section title="EmptyState">
          <div className="w-full">
            <EmptyState
              icon={<BrandMark size={32} className="opacity-40" />}
              title="아직 대국이 없습니다"
              description="첫 대국을 시작해 기보를 쌓아보세요."
              action={<Button>새 대국</Button>}
            />
          </div>
        </Section>

        <Section title="Card">
          <Card className="w-80">
            <CardHeader><CardTitle>최근 대국</CardTitle></CardHeader>
            <CardContent>
              <PlayerCaption color="black" name="rarebirds" rank="1단" />
              <Separator className="my-3" />
              <div className="font-mono text-xs text-ink-mute">2026-04-19 · 9×9 · 승</div>
            </CardContent>
          </Card>
        </Section>
      </div>
    </TooltipProvider>
  );
}
```

- [ ] **Step 2: Verify the catalog renders**

```bash
cd web && (curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/dev/components || echo "dev server needs restart after Tailwind config change")
```
Expected: 200. Open http://localhost:3000/dev/components in a browser and confirm: every section renders in both Day and Night, no console errors, no hardcoded purple/AI-ish colors, Newsreader headings, Pretendard body text, Plex Mono numbers.

- [ ] **Step 3: Commit**

```bash
git add web/app/dev/components/page.tsx
git commit -m "feat(web): /dev/components catalog page for Phase 1 visual verification"
```

---

## Task 27 — Final Verification

**Files:** (no source changes; verification only)

- [ ] **Step 1: Typecheck entire web/**

```bash
cd web && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 2: Lint**

```bash
cd web && npm run lint
```
Expected: no errors or warnings.

- [ ] **Step 3: Run all Vitest tests**

```bash
cd web && npm test -- --run
```
Expected: all tests pass (existing + new Button, BrandMark, StatFigure, DataBlock, cn).

- [ ] **Step 4: Build check**

```bash
cd web && npm run build
```
Expected: successful production build. If failing, fix before proceeding.

- [ ] **Step 5: Dev smoke (manual)**

Open http://localhost:3000/ and http://localhost:3000/dev/components in the browser. In each:
- Toggle Day / Night / System — check no flash on reload
- Inspect body background: should be `rgb(245 239 230)` (light) or `rgb(28 25 23)` (dark)
- Verify Newsreader loads (check H1 in catalog page), Pretendard loads (body text), Plex Mono loads (numbers in StatFigure)

- [ ] **Step 6: Guardian audit (optional)**

Invoke the `design-token-guardian` agent to audit `web/components/ui/` and `web/components/editorial/` for token compliance.

- [ ] **Step 7: Final commit (if any polish needed)**

If the catalog or primitives needed tweaks:
```bash
git add -A web/
git commit -m "fix(web): Phase 1 foundation polish post-verification"
```

---

## Success Criteria for Phase 1

- [ ] 12 shadcn primitives live in `web/components/ui/`
- [ ] 9 editorial primitives + icons live in `web/components/editorial/`
- [ ] `/dev/components` renders all of them in both Day/Night themes without errors
- [ ] No hardcoded hex colors in new files (design-token-check.sh hook silent)
- [ ] Vitest suite green (existing + new tests)
- [ ] `npm run build` succeeds
- [ ] Existing user-facing screens (home, login, history, etc.) still render — visual change limited to paper background, body text color, and serif headings

---

## Next Phase

After Phase 1 lands, return to `superpowers:writing-plans` with this spec to author Phase 2 (Core Flow — TopNav/Home/NewGame/Play/Review). Phase 2 will use the `editorial-implementer` agent dispatched in parallel, one agent per screen, with `design-token-guardian` + `visual-qa` follow-up gates.

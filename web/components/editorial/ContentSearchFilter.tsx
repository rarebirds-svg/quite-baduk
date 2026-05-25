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

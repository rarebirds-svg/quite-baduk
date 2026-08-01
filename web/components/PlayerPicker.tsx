"use client";
import { useState } from "react";
import { useT } from "@/lib/i18n";
import type { AiStyle } from "@/components/StylePicker";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export type PlayerId =
  | "lee_changho"
  | "cho_chikun"
  | "kobayashi_koichi"
  | "takemiya_masaki"
  | "fujisawa_shuko"
  | "otake_hideo"
  | "yoo_changhyuk"
  | "sakata_eio"
  | "lee_sedol"
  | "gu_li"
  | "cho_hunhyun"
  | "kato_masao"
  | "go_seigen"
  | "kitani_minoru"
  | "park_junghwan"
  | "shin_jinseo"
  | "ke_jie"
  | "seo_bongsoo"
  | "choi_cheolhan";

// Career-peak year — surfaced as a tiny mono badge so the picker reads as
// a roster of distinct eras rather than a flat list. Source of truth lives
// on the backend in app.core.katago.players; we mirror it here so the new-
// game form can render without a fetch.
export const PLAYER_META: Record<PlayerId, { proyear: number }> = {
  lee_changho:       { proyear: 1998 },
  cho_chikun:        { proyear: 1984 },
  kobayashi_koichi:  { proyear: 1988 },
  takemiya_masaki:   { proyear: 1986 },
  fujisawa_shuko:    { proyear: 1978 },
  otake_hideo:       { proyear: 1975 },
  yoo_changhyuk:     { proyear: 1998 },
  sakata_eio:        { proyear: 1962 },
  lee_sedol:         { proyear: 2012 },
  gu_li:             { proyear: 2010 },
  cho_hunhyun:       { proyear: 1990 },
  kato_masao:        { proyear: 1980 },
  go_seigen:         { proyear: 1950 },
  kitani_minoru:     { proyear: 1940 },
  park_junghwan:     { proyear: 2018 },
  shin_jinseo:       { proyear: 2023 },
  ke_jie:            { proyear: 2019 },
  seo_bongsoo:       { proyear: 1992 },
  choi_cheolhan:     { proyear: 2005 },
};

// 각 기사의 국적 (2-letter ISO) — 관전·복기 화면에서 AI 상대 국기 표기에 쓴다.
// 오청원(go_seigen)은 중국 출생·일본 활동의 경계적 인물이라 출생지 기준 CN.
export const PLAYER_COUNTRY: Record<PlayerId, string> = {
  lee_changho:      "KR",
  cho_chikun:       "KR",
  kobayashi_koichi: "JP",
  takemiya_masaki:  "JP",
  fujisawa_shuko:   "JP",
  otake_hideo:      "JP",
  yoo_changhyuk:    "KR",
  sakata_eio:       "JP",
  lee_sedol:        "KR",
  gu_li:            "CN",
  cho_hunhyun:      "KR",
  kato_masao:       "JP",
  go_seigen:        "CN",
  kitani_minoru:    "JP",
  park_junghwan:    "KR",
  shin_jinseo:      "KR",
  ke_jie:           "CN",
  seo_bongsoo:      "KR",
  choi_cheolhan:    "KR",
};

// Grouped in the same order the picker should display.
export const PLAYER_GROUPS: { style: AiStyle; players: PlayerId[] }[] = [
  { style: "territorial", players: ["lee_changho", "kobayashi_koichi"] },
  { style: "influence",   players: ["takemiya_masaki", "fujisawa_shuko", "otake_hideo"] },
  { style: "combative",   players: ["yoo_changhyuk", "sakata_eio", "cho_chikun", "lee_sedol", "gu_li"] },
  { style: "speed",       players: ["cho_hunhyun", "kato_masao"] },
  { style: "classical",   players: ["go_seigen", "kitani_minoru"] },
  { style: "balanced",    players: ["park_junghwan", "shin_jinseo", "ke_jie"] },
  { style: "rustic",      players: ["seo_bongsoo", "choi_cheolhan"] },
];

export const ALL_PLAYER_IDS: readonly PlayerId[] = PLAYER_GROUPS.flatMap(
  (g) => g.players,
);

export function randomPlayerId(): PlayerId {
  return ALL_PLAYER_IDS[Math.floor(Math.random() * ALL_PLAYER_IDS.length)];
}

export interface PlayerPickerProps {
  value: PlayerId | null;
  onChange: (p: PlayerId) => void;
}

export default function PlayerPicker({ value, onChange }: PlayerPickerProps) {
  const t = useT();
  const resolvedLabel = t("game.aiPlayer");
  // Detail dialog: open with a specific player's id, null when closed.
  // Click on the card body still selects the player (existing behaviour);
  // the small ⓘ button is a separate target that opens the dialog without
  // selecting, so a curious user can browse without committing.
  const [detailOf, setDetailOf] = useState<PlayerId | null>(null);
  // 기풍 필터 — 19명을 한 번에 펼치는 과부하를 줄인다. "전체"면 전 그룹 표시.
  const [styleFilter, setStyleFilter] = useState<AiStyle | "all">("all");
  const visibleGroups =
    styleFilter === "all"
      ? PLAYER_GROUPS
      : PLAYER_GROUPS.filter((g) => g.style === styleFilter);

  // Resolve the style for whichever player the dialog is showing — so we
  // can pull the style label/desc keys out of i18n without storing a copy.
  const styleOf: AiStyle | null = detailOf
    ? (PLAYER_GROUPS.find((g) => g.players.includes(detailOf))?.style ?? null)
    : null;

  const filterChip = (active: boolean) =>
    "rounded-full px-3 py-1 font-sans text-xs font-semibold transition-base " +
    (active
      ? "bg-ink text-paper"
      : "border border-ink-faint text-ink-mute hover:border-ink-mute hover:text-ink");

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-1.5" role="group" aria-label={t("game.styleFilterLabel")}>
        <button
          type="button"
          aria-pressed={styleFilter === "all"}
          onClick={() => setStyleFilter("all")}
          className={filterChip(styleFilter === "all")}
        >
          {t("game.styleFilterAll")}
        </button>
        {PLAYER_GROUPS.map((g) => (
          <button
            key={g.style}
            type="button"
            aria-pressed={styleFilter === g.style}
            onClick={() => setStyleFilter(g.style)}
            className={filterChip(styleFilter === g.style)}
          >
            {t(`game.aiStyleName.${g.style}`)}
          </button>
        ))}
      </div>
      <div role="radiogroup" aria-label={resolvedLabel} className="flex flex-col gap-5">
        {visibleGroups.map((group) => (
          <div key={group.style} className="flex flex-col gap-2">
            <div className="flex items-baseline justify-between">
              <span className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood">
                {t(`game.aiStyleName.${group.style}`)}
              </span>
              <span className="font-sans text-xs text-ink-faint">
                {t(`game.aiStyleDesc.${group.style}`)}
              </span>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {group.players.map((pid) => {
                const selected = pid === value;
                const year = PLAYER_META[pid].proyear;
                return (
                  <div
                    key={pid}
                    className={
                      "relative flex flex-col gap-1 border px-3 py-2 transition-base " +
                      (selected
                        ? "border-oxblood bg-paper-deep"
                        : "border-ink-faint hover:border-ink-mute")
                    }
                  >
                    <button
                      type="button"
                      role="radio"
                      aria-checked={selected}
                      onClick={() => onChange(pid)}
                      className="flex flex-col gap-1 text-left -m-3 -mb-2 px-3 py-2 pb-1"
                    >
                      <div className="flex items-baseline justify-between gap-2">
                        <span className="font-serif text-base text-ink">
                          {t(`game.players.${pid}.name`)}
                        </span>
                        <span className="font-mono text-[10px] tabular-nums text-ink-mute">
                          {year}
                        </span>
                      </div>
                      <span className="font-sans text-xs text-ink-mute">
                        {t(`game.players.${pid}.bio`)}
                      </span>
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDetailOf(pid);
                      }}
                      aria-label={t("game.playerDetail")}
                      className="absolute bottom-1 right-1 inline-flex h-6 w-6 items-center justify-center rounded-full border border-ink-faint text-ink-mute hover:border-oxblood hover:text-oxblood font-serif text-[11px] leading-none"
                    >
                      i
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <p className="font-sans text-xs text-ink-faint leading-relaxed border-t border-ink-faint pt-3">
        {t("game.playerNamesDisclaimer")}
      </p>

      <Dialog
        open={detailOf !== null}
        onOpenChange={(open) => {
          if (!open) setDetailOf(null);
        }}
      >
        <DialogContent className="max-w-md">
          {detailOf && styleOf && (
            <>
              <DialogHeader>
                <DialogTitle className="font-serif text-2xl text-ink">
                  {t(`game.players.${detailOf}.name`)}
                </DialogTitle>
                <DialogDescription className="flex flex-wrap items-baseline gap-3 font-sans text-xs">
                  <span className="font-mono tabular-nums text-ink-mute">
                    {PLAYER_META[detailOf].proyear}
                  </span>
                  <span className="font-semibold uppercase tracking-label text-oxblood">
                    {t(`game.aiStyleName.${styleOf}`)}
                  </span>
                  <span className="text-ink-faint">
                    {t(`game.aiStyleDesc.${styleOf}`)}
                  </span>
                </DialogDescription>
              </DialogHeader>
              <div className="flex flex-col gap-4 mt-2">
                <p className="font-serif text-base leading-relaxed text-ink">
                  {t(`game.players.${detailOf}.bio`)}
                </p>
                <div className="flex justify-end gap-2 pt-2 border-t border-ink-faint">
                  <Button
                    variant="outline"
                    onClick={() => setDetailOf(null)}
                  >
                    {t("game.close")}
                  </Button>
                  <Button
                    onClick={() => {
                      if (detailOf) onChange(detailOf);
                      setDetailOf(null);
                    }}
                  >
                    {t("game.selectPlayer")}
                  </Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

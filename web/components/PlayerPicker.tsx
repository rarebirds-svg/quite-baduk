"use client";
import { useT } from "@/lib/i18n";
import type { AiStyle } from "@/components/StylePicker";

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
  | "seo_bongsoo";

// Grouped in the same order the picker should display.
export const PLAYER_GROUPS: { style: AiStyle; players: PlayerId[] }[] = [
  { style: "territorial", players: ["lee_changho", "cho_chikun", "kobayashi_koichi"] },
  { style: "influence",   players: ["takemiya_masaki", "fujisawa_shuko", "otake_hideo"] },
  { style: "combative",   players: ["yoo_changhyuk", "sakata_eio", "lee_sedol", "gu_li"] },
  { style: "speed",       players: ["cho_hunhyun", "kato_masao"] },
  { style: "classical",   players: ["go_seigen", "kitani_minoru"] },
  { style: "balanced",    players: ["park_junghwan", "shin_jinseo", "ke_jie"] },
  { style: "rustic",      players: ["seo_bongsoo"] },
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

  return (
    <div className="flex flex-col gap-4">
      <div role="radiogroup" aria-label={resolvedLabel} className="flex flex-col gap-5">
        {PLAYER_GROUPS.map((group) => (
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
                return (
                  <button
                    key={pid}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    onClick={() => onChange(pid)}
                    className={
                      "flex flex-col gap-1 border px-3 py-2 text-left transition-base " +
                      (selected
                        ? "border-oxblood bg-paper-deep"
                        : "border-ink-faint hover:border-ink-mute")
                    }
                  >
                    <span className="font-serif text-base text-ink">
                      {t(`game.players.${pid}.name`)}
                    </span>
                    <span className="font-sans text-xs text-ink-mute">
                      {t(`game.players.${pid}.bio`)}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

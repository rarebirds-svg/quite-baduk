"use client";
// 기풍별 "추천 1인" 큐레이션 — 19명 과부하 대신 대표 기사를 먼저 제시하고, 원하면 전체 로스터를 펼친다
import { useState } from "react";
import { useT } from "@/lib/i18n";
import type { AiStyle } from "@/components/StylePicker";
import PlayerPicker, {
  type PlayerId,
  PLAYER_GROUPS,
} from "@/components/PlayerPicker";

// 각 기풍의 대표(추천) 기사 — 그 기풍에서 가장 상징적인 이름 1인.
const STYLE_REPRESENTATIVE: Record<AiStyle, PlayerId> = {
  territorial: "lee_changho",
  influence: "takemiya_masaki",
  combative: "lee_sedol",
  speed: "cho_hunhyun",
  classical: "go_seigen",
  balanced: "shin_jinseo",
  rustic: "seo_bongsoo",
};

export interface OpponentCurationProps {
  value: PlayerId | null;
  onChange: (p: PlayerId) => void;
}

export default function OpponentCuration({ value, onChange }: OpponentCurationProps) {
  const t = useT();
  const [showAll, setShowAll] = useState(false);

  const styleOfValue = value
    ? PLAYER_GROUPS.find((g) => g.players.includes(value))?.style ?? null
    : null;

  return (
    <div className="flex flex-col gap-4">
      <div role="radiogroup" aria-label={t("game.opponentRecommended")} className="flex flex-col gap-2">
        {PLAYER_GROUPS.map((group) => {
          const selectedInGroup = styleOfValue === group.style;
          // 이 기풍의 기사를 이미 골랐다면 그 이름을, 아니면 대표 기사를 보여준다.
          const shownPlayer =
            selectedInGroup && value ? value : STYLE_REPRESENTATIVE[group.style];
          return (
            <button
              key={group.style}
              type="button"
              role="radio"
              aria-checked={selectedInGroup}
              onClick={() => onChange(shownPlayer)}
              className={
                "flex items-center justify-between gap-3 rounded-sm border px-4 py-3 text-left transition-base " +
                (selectedInGroup
                  ? "border-oxblood bg-paper-deep"
                  : "border-ink-faint hover:border-ink-mute")
              }
            >
              <span className="flex flex-col gap-0.5">
                <span className="font-serif text-base text-ink">
                  {t(`game.aiStyleName.${group.style}`)}
                </span>
                <span className="font-sans text-xs text-ink-mute">
                  {t(`game.aiStyleDesc.${group.style}`)}
                </span>
              </span>
              <span className="flex shrink-0 items-center gap-2">
                <span className="font-sans text-sm text-ink-mute">
                  {t(`game.players.${shownPlayer}.name`)}
                </span>
                <span
                  aria-hidden
                  className={
                    "h-2 w-2 rounded-full " +
                    (selectedInGroup ? "bg-oxblood" : "bg-transparent")
                  }
                />
              </span>
            </button>
          );
        })}
      </div>

      <button
        type="button"
        aria-expanded={showAll}
        onClick={() => setShowAll((v) => !v)}
        className="self-start font-sans text-xs font-semibold text-oxblood hover:underline"
      >
        {showAll ? t("game.opponentBrowseLess") : t("game.opponentBrowseAll")}
      </button>

      {showAll && <PlayerPicker value={value} onChange={onChange} />}
    </div>
  );
}

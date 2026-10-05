"use client";
// 대국 시작 인트로 카드 — 선택한 레전드 기사의 이름·활동기·한 줄 소개를 첫 수
// 전에 보여줘 "오청원 5급" 텍스트만으로는 부족한 캐릭터 몰입감을 채운다.
import { X } from "lucide-react";
import { useT, useLocale } from "@/lib/i18n";
import { CountryFlag } from "@/components/CountryFlag";
import { PLAYER_COUNTRY, PLAYER_META, type PlayerId } from "@/components/PlayerPicker";
import { withJosa } from "@/lib/hangul";

export interface PersonaIntroProps {
  playerId: PlayerId;
  /** "5급 · 실리형"처럼 이미 조합된 급수·기풍 라벨 */
  rankLabel: string;
  onDismiss: () => void;
}

export function PersonaIntro({ playerId, rankLabel, onDismiss }: PersonaIntroProps) {
  const t = useT();
  const [locale] = useLocale();
  const name = t(`game.players.${playerId}.name`);
  const bio = t(`game.players.${playerId}.bio`);
  const year = PLAYER_META[playerId]?.proyear;
  const title =
    locale === "ko"
      ? t("game.personaIntro.title", { name: withJosa(name, "과", "와") })
      : t("game.personaIntro.title", { name });
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-start gap-3 border border-ink bg-paper-deep px-4 py-3 font-sans"
    >
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p className="font-serif text-base leading-snug text-ink">{title}</p>
        <p className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-ink-mute">
          <CountryFlag code={PLAYER_COUNTRY[playerId]} />
          {year && (
            <span className="font-mono tabular-nums">
              {t("game.personaIntro.peak", { year: String(year) })}
            </span>
          )}
          <span className="font-mono">{rankLabel}</span>
        </p>
        <p className="text-sm leading-relaxed text-ink">{bio}</p>
      </div>
      <button
        type="button"
        onClick={onDismiss}
        aria-label={t("game.personaIntro.dismiss")}
        className="shrink-0 text-ink-faint hover:text-ink"
      >
        <X size={14} strokeWidth={1.5} />
      </button>
    </div>
  );
}

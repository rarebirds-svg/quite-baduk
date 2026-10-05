"use client";
// 기사 인트로·코멘트 켜기/끄기 — 설정 화면용.
import { useEffect, useState } from "react";
import { MessageSquare, MessageSquareOff } from "lucide-react";
import { useT } from "@/lib/i18n";
import { usePersonaPref } from "@/store/personaPrefStore";

export default function PersonaCommentToggle({ className = "" }: { className?: string }) {
  const t = useT();
  const on = usePersonaPref((s) => s.commentary);
  const setOn = usePersonaPref((s) => s.setCommentary);
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const active = mounted ? on : true;
  return (
    <div className={`flex items-center justify-between gap-3 ${className}`}>
      <span className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
        {t("settings.personaCommentary")}
      </span>
      <button
        type="button"
        onClick={() => setOn(!active)}
        aria-pressed={active}
        className="flex h-8 items-center gap-2 rounded-full border border-ink/15 px-3 font-sans text-xs font-semibold text-ink-mute transition-base hover:text-ink"
      >
        {active ? (
          <MessageSquare size={16} strokeWidth={1.5} aria-hidden />
        ) : (
          <MessageSquareOff size={16} strokeWidth={1.5} aria-hidden />
        )}
        <span>{active ? t("settings.personaCommentaryOn") : t("settings.personaCommentaryOff")}</span>
      </button>
    </div>
  );
}

"use client";
// 착수음 켜기/끄기 버튼 — 대국 사이드바·설정 화면에서 공유한다.
// 상태는 lib/soundfx.ts가 localStorage(sfx:stone)에 들고 있다.
import { useEffect, useState } from "react";
import { Volume2, VolumeX } from "lucide-react";
import { useT } from "@/lib/i18n";
import { isStoneSoundEnabled, setStoneSoundEnabled } from "@/lib/soundfx";

export default function SoundToggle({ className = "" }: { className?: string }) {
  const t = useT();
  // SSR에서는 localStorage를 못 읽으므로 마운트 후 실제 값을 반영한다.
  const [on, setOn] = useState(true);
  useEffect(() => setOn(isStoneSoundEnabled()), []);
  const toggle = () => {
    const next = !on;
    setOn(next);
    setStoneSoundEnabled(next);
  };
  return (
    <div className={`flex items-center justify-between gap-3 ${className}`}>
      <span className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
        {t("settings.stoneSound")}
      </span>
      <button
        type="button"
        onClick={toggle}
        aria-pressed={on}
        aria-label={on ? t("review.soundOff") : t("review.soundOn")}
        title={on ? t("review.soundOff") : t("review.soundOn")}
        className="flex h-8 items-center gap-2 rounded-full border border-ink/15 px-3 font-sans text-xs font-semibold text-ink-mute transition-base hover:text-ink"
      >
        {on ? (
          <Volume2 size={16} strokeWidth={1.5} aria-hidden />
        ) : (
          <VolumeX size={16} strokeWidth={1.5} aria-hidden />
        )}
        <span>{on ? t("settings.stoneSoundOn") : t("settings.stoneSoundOff")}</span>
      </button>
    </div>
  );
}

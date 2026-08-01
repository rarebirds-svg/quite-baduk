"use client";
// 형세 표시 밀도(초보/분석가)를 전환하는 세그먼트 토글
import { useEffect, useState } from "react";
import { useT } from "@/lib/i18n";
import { useAnalysisPref, type AnalysisDensity } from "@/store/analysisPrefStore";

const OPTIONS: { value: AnalysisDensity; key: string }[] = [
  { value: "beginner", key: "game.viewBeginner" },
  { value: "analyst", key: "game.viewAnalyst" },
];

export default function AnalysisDensityToggle({ className = "" }: { className?: string }) {
  const t = useT();
  const density = useAnalysisPref((s) => s.density);
  const setDensity = useAnalysisPref((s) => s.setDensity);
  // persist는 클라이언트에서 동기 rehydrate되므로 SSR 기본값과 어긋날 수 있다.
  // 마운트 후에만 실제 값을 반영해 hydration mismatch를 피한다.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const active: AnalysisDensity = mounted ? density : "analyst";

  return (
    <div className={`flex items-center justify-between gap-3 ${className}`}>
      <span className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
        {t("game.analysisView")}
      </span>
      <div
        role="group"
        aria-label={t("game.analysisView")}
        className="flex rounded-full border border-ink/15 p-0.5"
      >
        {OPTIONS.map((o) => {
          const on = active === o.value;
          return (
            <button
              key={o.value}
              type="button"
              aria-pressed={on}
              onClick={() => setDensity(o.value)}
              className={`rounded-full px-3 py-1 font-sans text-xs font-semibold transition-base ${
                on
                  ? "bg-ink text-paper"
                  : "text-ink-mute hover:text-ink"
              }`}
            >
              {t(o.key)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

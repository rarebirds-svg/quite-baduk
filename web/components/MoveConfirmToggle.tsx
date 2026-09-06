"use client";
// 착수 방식(자동/한 번에/확인 후) 세그먼트 토글 — 설정 화면용.
import { useEffect, useState } from "react";
import { useT } from "@/lib/i18n";
import { useMovePref, type MoveConfirmPref } from "@/store/movePrefStore";

const OPTIONS: { value: MoveConfirmPref; key: string }[] = [
  { value: "auto", key: "settings.moveConfirm_auto" },
  { value: "tap", key: "settings.moveConfirm_tap" },
  { value: "confirm", key: "settings.moveConfirm_confirm" },
];

export default function MoveConfirmToggle({ className = "" }: { className?: string }) {
  const t = useT();
  const pref = useMovePref((s) => s.moveConfirm);
  const setPref = useMovePref((s) => s.setMoveConfirm);
  // persist는 클라이언트에서 동기 rehydrate되므로 마운트 후에만 실제 값을 반영한다.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const active: MoveConfirmPref = mounted ? pref : "auto";

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <span className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
        {t("settings.moveConfirm")}
      </span>
      <div
        role="group"
        aria-label={t("settings.moveConfirm")}
        className="flex self-start rounded-full border border-ink/15 p-0.5"
      >
        {OPTIONS.map((o) => {
          const on = active === o.value;
          return (
            <button
              key={o.value}
              type="button"
              aria-pressed={on}
              onClick={() => setPref(o.value)}
              className={`rounded-full px-3 py-1 font-sans text-xs font-semibold transition-base ${
                on ? "bg-ink text-paper" : "text-ink-mute hover:text-ink"
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

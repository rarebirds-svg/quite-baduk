"use client";
// 한 세션당 한 번만 보이는 부드러운 후원 안내 카드. 게임 종료/일일 챌린지
// streak 등 의미 있는 모먼트에 mount 시 자동 표시되도록 부모가 호출.
import { useEffect, useState } from "react";
import Link from "next/link";
import { X } from "lucide-react";
import { useT } from "@/lib/i18n";

const SESSION_KEY = "inkbaduk:support-nudge-dismissed";

export interface SupportNudgeProps {
  /** sessionStorage 키에 합쳐 같은 세션에 중복 노출 방지. 미지정 시 default. */
  context?: string;
}

export function SupportNudge({ context = "default" }: SupportNudgeProps) {
  const t = useT();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const v = window.sessionStorage.getItem(`${SESSION_KEY}:${context}`);
      if (v !== "1") setVisible(true);
    } catch {
      // sessionStorage 차단(프라이빗 모드 등) — 안전하게 노출.
      setVisible(true);
    }
  }, [context]);

  const dismiss = () => {
    setVisible(false);
    try {
      window.sessionStorage.setItem(`${SESSION_KEY}:${context}`, "1");
    } catch {
      // 무시.
    }
  };

  if (!visible) return null;

  return (
    <aside
      className="border border-ink-faint bg-paper-deep px-4 py-3 flex items-baseline gap-3 font-sans text-sm"
      aria-live="polite"
    >
      <span className="text-ink-mute leading-relaxed">
        {t("support.nudge")}{" "}
        <Link href="/support" className="text-oxblood hover:underline">
          {t("support.nudgeCta")} →
        </Link>
      </span>
      <button
        type="button"
        onClick={dismiss}
        aria-label={t("support.nudgeDismiss")}
        className="ml-auto shrink-0 text-ink-faint hover:text-ink"
      >
        <X size={14} strokeWidth={1.5} />
      </button>
    </aside>
  );
}

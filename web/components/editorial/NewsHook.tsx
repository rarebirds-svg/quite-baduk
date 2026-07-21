"use client";
// 홈 랜딩 히어로용 타임리 뉴스 훅 — 화제성 뉴스 유입을 대국 시작으로 전환. 뉴스가 식으면 이 파일과 page.tsx의 렌더 한 줄만 지우면 됨
import { Newspaper } from "lucide-react";
import { useT } from "@/lib/i18n";

/**
 * Small wire-dispatch style callout tied to a specific real-world event.
 * Intentionally isolated: delete this file and its single call site in
 * `app/page.tsx` to retire the hook once the news cools down.
 */
export function NewsHook() {
  const t = useT();
  return (
    <div className="mt-8 flex flex-col gap-3 border border-oxblood/30 rounded-sm bg-oxblood/5 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
      <div className="flex items-start gap-3">
        <Newspaper size={16} strokeWidth={1.5} className="mt-0.5 shrink-0 text-oxblood" aria-hidden="true" />
        <p className="font-sans text-sm leading-relaxed text-ink">
          <span className="font-semibold uppercase tracking-widest text-xs text-oxblood mr-2">
            {t("home.newsHook.kicker")}
          </span>
          {t("home.newsHook.body")}
        </p>
      </div>
      <a
        href="#start"
        className="shrink-0 border border-ink bg-ink rounded-sm px-5 py-2.5 text-center font-sans text-xs font-semibold uppercase tracking-label text-paper transition-base hover:bg-oxblood hover:border-oxblood"
      >
        {t("home.newsHook.cta")}
      </a>
    </div>
  );
}

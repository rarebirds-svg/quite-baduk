"use client";
// 홈 랜딩 히어로용 타임리 뉴스 훅 — 화제성 뉴스 유입을 대국 시작으로 전환. 뉴스가 식으면 이 파일과 page.tsx의 렌더 한 줄만 지우면 됨
import { ArrowDown, Newspaper } from "lucide-react";
import { useT } from "@/lib/i18n";

/**
 * Small wire-dispatch style callout tied to a specific real-world event.
 * Intentionally isolated: delete this file and its single call site in
 * `app/page.tsx` to retire the hook once the news cools down.
 */
export function NewsHook() {
  const t = useT();
  return (
    <div className="mt-8 flex items-start gap-3 border border-oxblood/30 rounded-sm bg-oxblood/5 px-5 py-4">
      <Newspaper size={16} strokeWidth={1.5} className="mt-0.5 shrink-0 text-oxblood" aria-hidden="true" />
      <div className="flex flex-col gap-2">
        <p className="font-sans text-sm leading-relaxed text-ink">
          <span className="font-semibold uppercase tracking-widest text-xs text-oxblood mr-2">
            {t("home.newsHook.kicker")}
          </span>
          {t("home.newsHook.body")}
        </p>
        <p className="flex items-center gap-1.5 font-sans text-sm text-ink-mute">
          <ArrowDown size={16} strokeWidth={1.5} className="shrink-0" aria-hidden="true" />
          {t("home.newsHook.guide")}
        </p>
      </div>
    </div>
  );
}

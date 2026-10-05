"use client";
// 홈 랜딩 히어로용 타임리 뉴스 훅 — 화제성 뉴스 유입을 대국 시작으로 전환.
// 본문(body/guide)은 web/content/news-hook.json에서 매주 자동 갱신된다(kicker만 i18n 고정 라벨).
import { ArrowDown, Newspaper } from "lucide-react";
import { useT, useLocale } from "@/lib/i18n";
import type { NewsHookData } from "@/lib/newsHook";

export function NewsHook({ data }: { data: NewsHookData | null }) {
  const t = useT();
  const [locale] = useLocale();
  if (!data) return null;
  const body = locale === "ko" ? data.body_ko : data.body_en;
  const guide = locale === "ko" ? data.guide_ko : data.guide_en;
  return (
    <div className="mt-8 flex items-start gap-3 border border-oxblood/30 rounded-sm bg-oxblood/5 px-5 py-4">
      <Newspaper size={16} strokeWidth={1.5} className="mt-0.5 shrink-0 text-oxblood" aria-hidden="true" />
      <div className="flex flex-col gap-2">
        <p className="font-sans text-sm leading-relaxed text-ink">
          <span className="font-semibold uppercase tracking-widest text-xs text-oxblood mr-2">
            {t("home.newsHook.kicker")}
          </span>
          {body}
        </p>
        <p className="flex items-center gap-1.5 font-sans text-sm text-ink-mute">
          <ArrowDown size={16} strokeWidth={1.5} className="shrink-0" aria-hidden="true" />
          {guide}
        </p>
      </div>
    </div>
  );
}

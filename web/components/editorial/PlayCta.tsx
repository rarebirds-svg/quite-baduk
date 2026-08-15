"use client";
// 콘텐츠 상세(글로서리·FAQ·프로기보)의 체험 전환 블록 — 오늘의 퍼즐과 즉시 대국 두 갈래를 제안한다.
import Link from "next/link";
import { Puzzle, Play } from "lucide-react";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/cn";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { Button } from "@/components/ui/button";
import QuickStartForm from "@/components/QuickStartForm";

export default function PlayCta({ className }: { className?: string }) {
  const t = useT();

  return (
    <section aria-label={t("playCta.divider")} className={cn("not-prose", className)}>
      <RuleDivider weight="strong" label={t("playCta.divider")} />

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {/* 좌 — 오늘의 퍼즐. 비로그인도 바로 풀 수 있다. */}
        <div className="flex flex-col gap-3 border border-ink-faint p-5">
          <p className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-label text-ink-faint">
            <Puzzle size={16} strokeWidth={1.5} aria-hidden />
            {t("playCta.puzzleEyebrow")}
          </p>
          <h2 className="font-serif text-xl text-ink">{t("playCta.puzzleTitle")}</h2>
          <p className="font-sans text-sm text-ink-mute">{t("playCta.puzzleBody")}</p>
          <Button asChild variant="outline" size="lg" className="mt-auto self-start">
            <Link href="/daily">{t("playCta.puzzleAction")}</Link>
          </Button>
        </div>

        {/* 우 — 닉네임 한 줄로 곧장 대국. QuickStartForm이 세션 유/무를 자체 처리한다. */}
        <div className="flex flex-col gap-3 border border-ink-faint p-5">
          <p className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-label text-ink-faint">
            <Play size={16} strokeWidth={1.5} aria-hidden />
            {t("playCta.playEyebrow")}
          </p>
          <h2 className="font-serif text-xl text-ink">{t("playCta.playTitle")}</h2>
          <p className="font-sans text-sm text-ink-mute">{t("playCta.playBody")}</p>
          <div className="mt-auto">
            <QuickStartForm autoFocus={false} />
          </div>
        </div>
      </div>
    </section>
  );
}

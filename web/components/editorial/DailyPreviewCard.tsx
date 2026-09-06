"use client";
// 홈 랜딩의 "오늘의 한 수" 미니 프리뷰 — 오늘 문제의 판·차례·주제를 보여주고
// /daily로 보낸다. 대국을 시작하지 않아도 매일 한 문제 풀고 가는 루틴용.
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { gtpToXy, totalCells } from "@/lib/board";
import Board from "@/components/Board";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { Button } from "@/components/ui/button";

interface SetupPlay {
  color: "B" | "W";
  coord: string;
}

export interface DailyChallengePreview {
  id: string;
  board_size: number;
  setup: SetupPlay[];
  to_move: "B" | "W";
  difficulty: string;
  topic: string;
  prompt_key: string;
}

export function buildPreviewBoard(size: number, setup: SetupPlay[]): string {
  const cells = Array.from({ length: totalCells(size) }, () => ".");
  for (const { color, coord } of setup) {
    const xy = gtpToXy(coord, size);
    if (!xy) continue;
    cells[xy[1] * size + xy[0]] = color;
  }
  return cells.join("");
}

export function DailyPreviewCard({ className = "" }: { className?: string }) {
  const t = useT();
  const [challenge, setChallenge] = useState<DailyChallengePreview | null>(null);
  useEffect(() => {
    let cancelled = false;
    api<DailyChallengePreview>("/api/daily-challenge")
      .then((c) => {
        if (!cancelled) setChallenge(c);
      })
      .catch(() => {
        // 프리뷰는 부가 요소 — 실패하면 조용히 숨긴다.
      });
    return () => {
      cancelled = true;
    };
  }, []);
  if (!challenge) return null;

  const board = buildPreviewBoard(challenge.board_size, challenge.setup);
  const prompt = t(challenge.prompt_key) === challenge.prompt_key
    ? t("daily.fallbackPrompt")
    : t(challenge.prompt_key);

  return (
    <section className={className} aria-labelledby="daily-preview-heading">
      <RuleDivider weight="faint" />
      <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-[minmax(0,180px)_1fr] md:gap-8">
        <div className="mx-auto w-full max-w-[180px] md:mx-0">
          <Board size={challenge.board_size} board={board} />
        </div>
        <div className="flex flex-col gap-3">
          <p className="font-sans text-xs font-semibold uppercase tracking-widest text-oxblood">
            {t("home.daily.eyebrow")}
          </p>
          <h2 id="daily-preview-heading" className="font-serif text-2xl leading-snug text-ink">
            {challenge.to_move === "B" ? t("daily.blackToMove") : t("daily.whiteToMove")}
          </h2>
          <p className="font-sans text-sm leading-relaxed text-ink-mute">{prompt}</p>
          <p className="flex flex-wrap gap-2 font-mono text-xs text-ink-mute">
            <span className="border border-ink-faint px-2 py-0.5">
              {t(`daily.topic.${challenge.topic}`)}
            </span>
            <span className="border border-ink-faint px-2 py-0.5">
              {t(`daily.difficulty.${challenge.difficulty}`)}
            </span>
            <span className="border border-ink-faint px-2 py-0.5 tabular-nums">
              {challenge.board_size}×{challenge.board_size}
            </span>
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-3">
            <Button asChild size="sm">
              <Link href="/daily">
                {t("home.daily.cta")}
                <ArrowRight size={16} strokeWidth={1.5} aria-hidden />
              </Link>
            </Button>
            <span className="font-sans text-xs text-ink-mute">{t("home.daily.hint")}</span>
          </div>
        </div>
      </div>
    </section>
  );
}

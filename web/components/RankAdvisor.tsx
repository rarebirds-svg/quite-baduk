"use client";
// 자기 급수를 모르는 입문자에게 2단계 문답으로 시작 급수를 추천하는 헬퍼
import { useState } from "react";
import { useT, useLocale } from "@/lib/i18n";
import { formatRank, type Rank } from "@/components/RankPicker";
import type { BoardSize } from "@/lib/board";

type Step = "closed" | "q1" | "q2" | "result";

export interface AdvisorResult {
  rank: Rank;
  boardSize: BoardSize;
}

// 문답 결과 → 급수 + 판 크기. 입문자는 9줄에서 시작해야 한 판을 끝까지 둘 수 있다.
export const ADVISOR_PRESETS = {
  q1New: { rank: "9k", boardSize: 9 },
  q1Rules: { rank: "7k", boardSize: 9 },
  q2Small: { rank: "5k", boardSize: 9 },
  q2Finish: { rank: "3k", boardSize: 19 },
  q2Club: { rank: "1k", boardSize: 19 },
  q2Dan: { rank: "2d", boardSize: 19 },
} as const satisfies Record<string, AdvisorResult>;

export default function RankAdvisor({
  onSelect,
}: {
  /** 적용 시 급수와 추천 판 크기를 함께 넘긴다 — 새 대국 폼이 둘 다 반영한다. */
  onSelect: (r: Rank, boardSize: BoardSize) => void;
}) {
  const t = useT();
  const [locale] = useLocale();
  const [step, setStep] = useState<Step>("closed");
  const [result, setResult] = useState<AdvisorResult | null>(null);

  const finish = (r: AdvisorResult) => {
    setResult(r);
    setStep("result");
  };

  const apply = () => {
    if (result) onSelect(result.rank, result.boardSize);
    setStep("closed");
  };

  if (step === "closed") {
    return (
      <button
        type="button"
        onClick={() => setStep("q1")}
        className="self-start font-sans text-xs font-semibold text-oxblood hover:underline"
      >
        {t("game.advisor.trigger")}
      </button>
    );
  }

  const Option = ({ label, onClick }: { label: string; onClick: () => void }) => (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-sm border border-ink/25 px-3 py-2 text-left font-sans text-sm text-ink transition-base hover:border-oxblood"
    >
      {label}
    </button>
  );

  return (
    <div className="flex flex-col gap-3 rounded-sm border border-ink-faint/50 bg-paper-deep/40 p-4">
      {step === "q1" && (
        <>
          <p className="font-sans text-sm font-semibold text-ink">{t("game.advisor.q1Title")}</p>
          <Option label={t("game.advisor.q1New")} onClick={() => finish(ADVISOR_PRESETS.q1New)} />
          <Option label={t("game.advisor.q1Rules")} onClick={() => finish(ADVISOR_PRESETS.q1Rules)} />
          <Option label={t("game.advisor.q1Played")} onClick={() => setStep("q2")} />
        </>
      )}
      {step === "q2" && (
        <>
          <p className="font-sans text-sm font-semibold text-ink">{t("game.advisor.q2Title")}</p>
          <Option label={t("game.advisor.q2Small")} onClick={() => finish(ADVISOR_PRESETS.q2Small)} />
          <Option label={t("game.advisor.q2Finish")} onClick={() => finish(ADVISOR_PRESETS.q2Finish)} />
          <Option label={t("game.advisor.q2Club")} onClick={() => finish(ADVISOR_PRESETS.q2Club)} />
          <Option label={t("game.advisor.q2Dan")} onClick={() => finish(ADVISOR_PRESETS.q2Dan)} />
        </>
      )}
      {step === "result" && result && (
        <>
          <p className="font-sans text-sm text-ink-mute">
            {t("game.advisor.resultLabel")}{" "}
            <span className="font-semibold text-ink">{formatRank(result.rank, locale)}</span>
            <span className="font-mono text-ink-faint"> · {result.boardSize}×{result.boardSize}</span>
          </p>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={apply}
              className="rounded-sm border border-ink bg-ink px-4 py-2 font-sans text-xs font-semibold uppercase tracking-label text-paper transition-base hover:border-oxblood hover:bg-oxblood"
            >
              {t("game.advisor.apply")}
            </button>
            <button
              type="button"
              onClick={() => setStep("q1")}
              className="font-sans text-xs text-ink-mute hover:underline"
            >
              {t("game.advisor.restart")}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

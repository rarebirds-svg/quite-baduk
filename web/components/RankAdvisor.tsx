"use client";
// 자기 급수를 모르는 입문자에게 2단계 문답으로 시작 급수를 추천하는 헬퍼
import { useState } from "react";
import { useT, useLocale } from "@/lib/i18n";
import { formatRank, type Rank } from "@/components/RankPicker";

type Step = "closed" | "q1" | "q2" | "result";

export default function RankAdvisor({ onSelect }: { onSelect: (r: Rank) => void }) {
  const t = useT();
  const [locale] = useLocale();
  const [step, setStep] = useState<Step>("closed");
  const [result, setResult] = useState<Rank | null>(null);

  const finish = (r: Rank) => {
    setResult(r);
    setStep("result");
  };

  const apply = () => {
    if (result) onSelect(result);
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
      className="w-full rounded-sm border border-ink/15 px-3 py-2 text-left font-sans text-sm text-ink transition-base hover:border-oxblood"
    >
      {label}
    </button>
  );

  return (
    <div className="flex flex-col gap-3 rounded-sm border border-ink-faint/50 bg-paper-deep/40 p-4">
      {step === "q1" && (
        <>
          <p className="font-sans text-sm font-semibold text-ink">{t("game.advisor.q1Title")}</p>
          <Option label={t("game.advisor.q1New")} onClick={() => finish("9k")} />
          <Option label={t("game.advisor.q1Rules")} onClick={() => finish("7k")} />
          <Option label={t("game.advisor.q1Played")} onClick={() => setStep("q2")} />
        </>
      )}
      {step === "q2" && (
        <>
          <p className="font-sans text-sm font-semibold text-ink">{t("game.advisor.q2Title")}</p>
          <Option label={t("game.advisor.q2Small")} onClick={() => finish("5k")} />
          <Option label={t("game.advisor.q2Finish")} onClick={() => finish("3k")} />
          <Option label={t("game.advisor.q2Club")} onClick={() => finish("1k")} />
          <Option label={t("game.advisor.q2Dan")} onClick={() => finish("2d")} />
        </>
      )}
      {step === "result" && result && (
        <>
          <p className="font-sans text-sm text-ink-mute">
            {t("game.advisor.resultLabel")}{" "}
            <span className="font-semibold text-ink">{formatRank(result, locale)}</span>
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

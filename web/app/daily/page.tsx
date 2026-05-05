"use client";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import Board from "@/components/Board";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { Button } from "@/components/ui/button";
import { gtpToXy, totalCells, xyToGtp } from "@/lib/board";
import { toast } from "sonner";

interface SetupPlay {
  color: "B" | "W";
  coord: string;
}

interface Challenge {
  id: string;
  board_size: number;
  setup: SetupPlay[];
  to_move: "B" | "W";
  difficulty: "easy" | "medium" | "hard";
  prompt_key: string;
}

interface AnswerResponse {
  verdict: "best" | "ok" | "weak" | "miss" | "illegal";
  winrate_before?: number;
  winrate_after?: number;
  drop?: number;
  top_moves: string[];
  user_captures?: number;
  detail?: string;
}

function buildBoard(size: number, setup: SetupPlay[]): string {
  const cells = Array.from({ length: totalCells(size) }, () => ".");
  for (const { color, coord } of setup) {
    const xy = gtpToXy(coord, size);
    if (!xy) continue;
    const [x, y] = xy;
    cells[y * size + x] = color;
  }
  return cells.join("");
}

export default function DailyChallengePage() {
  const t = useT();
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [candidate, setCandidate] = useState<{ x: number; y: number } | null>(
    null,
  );
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AnswerResponse | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const c = await api<Challenge>("/api/daily-challenge");
        setChallenge(c);
      } catch {
        setError("load_failed");
      }
    })();
  }, []);

  const baseBoard = useMemo(
    () => (challenge ? buildBoard(challenge.board_size, challenge.setup) : ""),
    [challenge],
  );

  // Project the user's tentative play onto the board so they can see where
  // they're committing before submission.
  const previewBoard = useMemo(() => {
    if (!challenge || !candidate) return baseBoard;
    const cells = baseBoard.split("");
    const idx = candidate.y * challenge.board_size + candidate.x;
    if (cells[idx] === ".") cells[idx] = challenge.to_move;
    return cells.join("");
  }, [baseBoard, candidate, challenge]);

  const onClickBoard = (x: number, y: number) => {
    if (!challenge || result || busy) return;
    const idx = y * challenge.board_size + x;
    if (baseBoard[idx] !== ".") return;
    setCandidate({ x, y });
  };

  const submit = async () => {
    if (!challenge || !candidate) return;
    setBusy(true);
    try {
      const coord = xyToGtp(candidate.x, candidate.y, challenge.board_size);
      const r = await api<AnswerResponse>(
        "/api/daily-challenge/answer",
        {
          method: "POST",
          body: JSON.stringify({ challenge_id: challenge.id, coord }),
        },
      );
      setResult(r);
    } catch {
      toast.error(t("daily.gradeFailed"));
    } finally {
      setBusy(false);
    }
  };

  const tryAgain = () => {
    setCandidate(null);
    setResult(null);
  };

  if (error) {
    return (
      <div className="p-4 text-oxblood">{t("errors.validation")}</div>
    );
  }

  if (!challenge) {
    return <div className="p-4 text-ink-mute">…</div>;
  }

  // Highlight recommended top moves once the user has submitted (always
  // shown alongside the verdict so the learning is concrete).
  const topOverlay =
    result && result.top_moves.length > 0
      ? result.top_moves
          .slice(0, 3)
          .map((mv, i) => {
            const xy = gtpToXy(mv, challenge.board_size);
            if (!xy) return null;
            return {
              x: xy[0],
              y: xy[1],
              color:
                i === 0
                  ? ("primary" as const)
                  : i === 1
                  ? ("secondary" as const)
                  : ("tertiary" as const),
              label: mv,
            };
          })
          .filter(
            (
              x,
            ): x is {
              x: number;
              y: number;
              color: "primary" | "secondary" | "tertiary";
              label: string;
            } => x !== null,
          )
      : undefined;

  const verdictTone: Record<AnswerResponse["verdict"], string> = {
    best: "border-moss text-moss",
    ok: "border-moss text-moss",
    weak: "border-gold text-gold",
    miss: "border-oxblood text-oxblood",
    illegal: "border-oxblood text-oxblood",
  };

  return (
    <div className="flex flex-col gap-6 py-4 max-w-3xl mx-auto px-4">
      <Hero
        volume={t("daily.eyebrow")}
        title={t("daily.title")}
        subtitle={
          t(`daily.prompts.${challenge.id}` as const) ||
          t("daily.fallbackPrompt")
        }
        size="compact"
      />

      <div className="flex items-baseline gap-3 font-sans text-xs">
        <span className="font-semibold uppercase tracking-label text-oxblood">
          {t(`daily.difficulty.${challenge.difficulty}`)}
        </span>
        <span className="text-ink-mute">
          {challenge.to_move === "B"
            ? t("daily.blackToMove")
            : t("daily.whiteToMove")}
        </span>
      </div>

      <RuleDivider />

      <div className="max-w-[min(560px,100%)] mx-auto w-full">
        <Board
          size={challenge.board_size}
          board={previewBoard}
          onClick={onClickBoard}
          disabled={busy || result !== null}
          overlay={topOverlay}
          lastMove={candidate}
        />
      </div>

      {!result && (
        <div className="flex items-center justify-between gap-3">
          <span className="font-mono text-xs tabular-nums text-ink-mute">
            {candidate
              ? xyToGtp(candidate.x, candidate.y, challenge.board_size)
              : t("daily.pickAMove")}
          </span>
          <Button
            onClick={submit}
            disabled={!candidate || busy}
          >
            {busy ? t("daily.grading") : t("daily.submit")}
          </Button>
        </div>
      )}

      {result && (
        <div
          className={
            "border px-4 py-3 flex flex-col gap-2 " + verdictTone[result.verdict]
          }
          aria-live="polite"
        >
          <div className="flex items-baseline justify-between gap-3">
            <span className="font-serif text-xl">
              {t(`daily.verdict.${result.verdict}`)}
            </span>
            {typeof result.drop === "number" && (
              <span className="font-mono text-sm tabular-nums">
                {result.drop > 0 ? "−" : "+"}
                {Math.abs(result.drop * 100).toFixed(1)}%
              </span>
            )}
          </div>
          {result.top_moves.length > 0 && (
            <div className="font-sans text-xs text-ink-mute flex items-baseline gap-2 flex-wrap">
              <span className="uppercase tracking-label">
                {t("daily.recommended")}
              </span>
              <span className="font-mono tabular-nums text-ink">
                {result.top_moves.slice(0, 3).join(" · ")}
              </span>
            </div>
          )}
          <div className="flex justify-end mt-1">
            <Button variant="outline" onClick={tryAgain} className="text-ink">
              {t("daily.tryAgain")}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

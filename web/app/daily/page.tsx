"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
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

type Topic =
  | "opening"
  | "joseki"
  | "life_death"
  | "tesuji"
  | "middle_game"
  | "endgame"
  | "capturing_race";
type Difficulty = "easy" | "medium" | "hard";
type BoardSize = 9 | 13 | 19;

interface Challenge {
  id: string;
  board_size: number;
  setup: SetupPlay[];
  to_move: "B" | "W";
  difficulty: Difficulty;
  topic: Topic;
  prompt_key: string;
}

interface Catalogue {
  board_sizes: BoardSize[];
  difficulties: Difficulty[];
  topics: Topic[];
  counts: Record<string, number>;
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

const TOPIC_OPTIONS: Topic[] = [
  "opening",
  "joseki",
  "life_death",
  "tesuji",
  "middle_game",
  "endgame",
  "capturing_race",
];
const DIFF_OPTIONS: Difficulty[] = ["easy", "medium", "hard"];
const SIZE_OPTIONS: BoardSize[] = [9, 13, 19];

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
  const [catalogue, setCatalogue] = useState<Catalogue | null>(null);

  // Filter state. `null` for any axis = "anything goes". Persisted in
  // localStorage so the user's chosen practice slice sticks across visits.
  const [boardSize, setBoardSize] = useState<BoardSize | null>(null);
  const [difficulty, setDifficulty] = useState<Difficulty | null>(null);
  const [topic, setTopic] = useState<Topic | null>(null);

  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [candidate, setCandidate] = useState<{ x: number; y: number } | null>(
    null,
  );
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AnswerResponse | null>(null);
  const [noMatch, setNoMatch] = useState(false);

  // Fetch catalogue once for the option lists + availability counts.
  useEffect(() => {
    (async () => {
      try {
        const c = await api<Catalogue>("/api/daily-challenge/catalogue");
        setCatalogue(c);
      } catch {
        // Non-fatal: filters degrade to "all enabled" if the catalogue
        // endpoint is unavailable.
      }
    })();
  }, []);

  // Restore filter state from localStorage once on mount.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const sz = window.localStorage.getItem("baduk.daily.size");
    const df = window.localStorage.getItem("baduk.daily.difficulty");
    const tp = window.localStorage.getItem("baduk.daily.topic");
    if (sz === "9" || sz === "13" || sz === "19") {
      setBoardSize(Number(sz) as BoardSize);
    }
    if (df === "easy" || df === "medium" || df === "hard") {
      setDifficulty(df);
    }
    if (tp && TOPIC_OPTIONS.includes(tp as Topic)) {
      setTopic(tp as Topic);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (boardSize !== null) {
      window.localStorage.setItem("baduk.daily.size", String(boardSize));
    } else {
      window.localStorage.removeItem("baduk.daily.size");
    }
  }, [boardSize]);
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (difficulty !== null) {
      window.localStorage.setItem("baduk.daily.difficulty", difficulty);
    } else {
      window.localStorage.removeItem("baduk.daily.difficulty");
    }
  }, [difficulty]);
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (topic !== null) {
      window.localStorage.setItem("baduk.daily.topic", topic);
    } else {
      window.localStorage.removeItem("baduk.daily.topic");
    }
  }, [topic]);

  // Fetch a puzzle: with filters → /random, without filters → /today.
  const fetchPuzzle = useCallback(async () => {
    setError(null);
    setNoMatch(false);
    setCandidate(null);
    setResult(null);
    try {
      const params = new URLSearchParams();
      if (boardSize !== null) params.set("board_size", String(boardSize));
      if (difficulty !== null) params.set("difficulty", difficulty);
      if (topic !== null) params.set("topic", topic);
      const hasFilter = params.toString().length > 0;
      const url = hasFilter
        ? `/api/daily-challenge/random?${params.toString()}`
        : `/api/daily-challenge`;
      const c = await api<Challenge>(url);
      setChallenge(c);
    } catch (e) {
      // 404 on /random when no puzzles match → show empty state.
      const status = (e as { status?: number })?.status;
      if (status === 404) {
        setChallenge(null);
        setNoMatch(true);
      } else {
        setError("load_failed");
      }
    }
  }, [boardSize, difficulty, topic]);

  // Refetch when filters change.
  useEffect(() => {
    fetchPuzzle();
  }, [fetchPuzzle]);

  const baseBoard = useMemo(
    () => (challenge ? buildBoard(challenge.board_size, challenge.setup) : ""),
    [challenge],
  );

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

  const nextPuzzle = () => {
    fetchPuzzle();
  };

  // Helper: is a particular filter value actually populated in the
  // current catalogue (intersected with the other active filters)? Used
  // to grey out empty options instead of letting the user pick a 404.
  const countFor = useCallback(
    (
      sz: BoardSize | null,
      df: Difficulty | null,
      tp: Topic | null,
    ): number => {
      if (!catalogue) return 1; // optimistic before catalogue lands
      const sizes = sz === null ? catalogue.board_sizes : [sz];
      const diffs = df === null ? catalogue.difficulties : [df];
      const tops = tp === null ? catalogue.topics : [tp];
      let total = 0;
      for (const s of sizes) {
        for (const d of diffs) {
          for (const tt of tops) {
            total += catalogue.counts[`${s}|${d}|${tt}`] ?? 0;
          }
        }
      }
      return total;
    },
    [catalogue],
  );

  const verdictTone: Record<AnswerResponse["verdict"], string> = {
    best: "border-moss text-moss",
    ok: "border-moss text-moss",
    weak: "border-gold text-gold",
    miss: "border-oxblood text-oxblood",
    illegal: "border-oxblood text-oxblood",
  };

  // Pill button used in every filter row.
  const Pill = ({
    active,
    disabled,
    onClick,
    children,
  }: {
    active: boolean;
    disabled?: boolean;
    onClick: () => void;
    children: React.ReactNode;
  }) => (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={
        "px-2.5 py-1 border font-sans text-[11px] sm:text-xs uppercase tracking-tight transition-base " +
        (disabled
          ? "border-ink-faint text-ink-faint cursor-not-allowed"
          : active
          ? "border-oxblood text-oxblood bg-paper-deep"
          : "border-ink-faint text-ink-mute hover:border-ink-mute")
      }
    >
      {children}
    </button>
  );

  return (
    <div className="flex flex-col gap-6 py-4 max-w-3xl mx-auto px-4">
      <Hero
        volume={t("daily.eyebrow")}
        title={t("daily.title")}
        subtitle={
          challenge
            ? // The backend supplies an i18n key directly (e.g.
              // "daily.topicPrompt.opening"); fall back to the generic
              // copy if the dictionary doesn't carry it for any reason.
              t(challenge.prompt_key as never) || t("daily.fallbackPrompt")
            : t("daily.fallbackPrompt")
        }
        size="compact"
      />

      {/* ── Filters ─────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 border border-ink-faint p-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood w-20">
            {t("daily.filterBoard")}
          </span>
          <Pill
            active={boardSize === null}
            onClick={() => setBoardSize(null)}
          >
            {t("daily.any")}
          </Pill>
          {SIZE_OPTIONS.map((s) => (
            <Pill
              key={s}
              active={boardSize === s}
              disabled={countFor(s, difficulty, topic) === 0}
              onClick={() => setBoardSize(s)}
            >
              {s}×{s}
            </Pill>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood w-20">
            {t("daily.filterTopic")}
          </span>
          <Pill active={topic === null} onClick={() => setTopic(null)}>
            {t("daily.any")}
          </Pill>
          {TOPIC_OPTIONS.map((tp) => (
            <Pill
              key={tp}
              active={topic === tp}
              disabled={countFor(boardSize, difficulty, tp) === 0}
              onClick={() => setTopic(tp)}
            >
              {t(`daily.topic.${tp}`)}
            </Pill>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood w-20">
            {t("daily.filterDifficulty")}
          </span>
          <Pill
            active={difficulty === null}
            onClick={() => setDifficulty(null)}
          >
            {t("daily.any")}
          </Pill>
          {DIFF_OPTIONS.map((d) => (
            <Pill
              key={d}
              active={difficulty === d}
              disabled={countFor(boardSize, d, topic) === 0}
              onClick={() => setDifficulty(d)}
            >
              {t(`daily.difficulty.${d}`)}
            </Pill>
          ))}
        </div>
      </div>

      {/* ── Puzzle area ─────────────────────────────────────────────── */}
      {error ? (
        <div className="p-4 text-oxblood">{t("errors.validation")}</div>
      ) : noMatch ? (
        <div className="border border-ink-faint p-6 text-center font-sans text-sm text-ink-mute">
          {t("daily.noMatch")}
        </div>
      ) : !challenge ? (
        <div className="p-4 text-ink-mute">…</div>
      ) : (
        <>
          <div className="flex items-baseline gap-3 font-sans text-xs">
            <span className="font-semibold uppercase tracking-label text-oxblood">
              {t(`daily.topic.${challenge.topic}`)}
            </span>
            <span className="text-ink-mute">
              {t(`daily.difficulty.${challenge.difficulty}`)}
            </span>
            <span className="text-ink-faint">
              {challenge.board_size}×{challenge.board_size}
            </span>
            <span className="text-ink-mute ml-auto">
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
              overlay={
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
                  : undefined
              }
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
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={nextPuzzle}
                  disabled={busy}
                >
                  {t("daily.skipNext")}
                </Button>
                <Button onClick={submit} disabled={!candidate || busy}>
                  {busy ? t("daily.grading") : t("daily.submit")}
                </Button>
              </div>
            </div>
          )}

          {result && (
            <div
              className={
                "border px-4 py-3 flex flex-col gap-2 " +
                verdictTone[result.verdict]
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
              <div className="flex justify-end gap-2 mt-1">
                <Button variant="outline" onClick={tryAgain} className="text-ink">
                  {t("daily.tryAgain")}
                </Button>
                <Button onClick={nextPuzzle}>
                  {t("daily.nextPuzzle")}
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

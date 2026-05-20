"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { Volume2, VolumeX } from "lucide-react";
import Board from "@/components/Board";
import { api } from "@/lib/api";
import { useT, useLocale } from "@/lib/i18n";
import { formatRank } from "@/components/RankPicker";
import { CountryFlag } from "@/components/CountryFlag";
import {
  applyMoveWithCaptures,
  gtpToXy,
  handicapStonesFor,
  totalCells,
} from "@/lib/board";
import { Button } from "@/components/ui/button";
import {
  isStoneSoundEnabled,
  playStoneClick,
  setStoneSoundEnabled,
} from "@/lib/soundfx";

interface MoveEntryRaw {
  move_number: number;
  color: "B" | "W";
  coord: string | null;
  is_undone: boolean;
}
interface GameDetail {
  id: number;
  board_size: number;
  handicap?: number;
  moves: MoveEntryRaw[];
  result: string | null;
  user_nickname?: string | null;
  user_rank?: string | null;
  user_country?: string | null;
  user_color?: "black" | "white";
  ai_player?: string | null;
  ai_style?: string;
  ai_rank?: string;
  started_at?: string;
  finished_at?: string | null;
}

interface AnalyzeResponse {
  winrate: number; // [0,1] — side-to-move's perspective at moveNum
  top_moves: { move: string; winrate: number; visits: number }[];
  ownership: number[];
}

// Move-position N (after N moves played) → Black's POV winrate.
function blackWinrateAt(
  sideToMoveWinrate: number,
  moveNum: number,
  handicap: number,
): number {
  const sideToMoveIsBlack = handicap > 0
    ? moveNum % 2 === 1
    : moveNum % 2 === 0;
  return sideToMoveIsBlack ? sideToMoveWinrate : 1 - sideToMoveWinrate;
}

// Drop in the moving player's winrate from before to after their move.
// Positive = mistake (the side that moved lost winrate).
function moveDrop(
  wrBlackBefore: number,
  wrBlackAfter: number,
  color: "B" | "W",
): number {
  return color === "B"
    ? wrBlackBefore - wrBlackAfter
    : wrBlackAfter - wrBlackBefore;
}

const BLUNDER_THRESHOLD = 0.10;

function replay(
  size: number,
  moves: MoveEntryRaw[],
  upto: number,
  handicap = 0,
): string {
  // Start from an empty board; pre-place handicap stones (never
  // persisted as MoveRow entries on the backend).
  let board = ".".repeat(totalCells(size));
  for (const coord of handicapStonesFor(size, handicap)) {
    const xy = gtpToXy(coord, size);
    if (!xy) continue;
    const cells = board.split("");
    cells[xy[1] * size + xy[0]] = "B";
    board = cells.join("");
  }
  // Apply each move via applyMoveWithCaptures so captured opponent
  // groups vanish exactly as they did during the live game. Without
  // this, the replay board accumulates dead stones that the player
  // already took off the board in real time.
  for (let i = 0; i < Math.min(upto, moves.length); i++) {
    const m = moves[i];
    if (m.is_undone || !m.coord || m.coord === "pass") continue;
    const xy = gtpToXy(m.coord, size);
    if (!xy) continue;
    board = applyMoveWithCaptures(board, size, xy[0], xy[1], m.color);
  }
  return board;
}

export interface ReviewPlayerProps {
  gameId: number;
  intervalMs?: number;
  autoplay?: boolean;
}

/**
 * Self-contained kifu replay with a single "감상 / 학습" mode toggle.
 *
 * Review mode (default): plain replay — board, scrubber, nav buttons.
 *
 * Learn mode (opt-in): analysis runs in the background; blunder dots
 * land on the scrubber as data arrives; whenever the current frame is
 * a blunder the board paints KataGo's top alternatives automatically
 * (no extra toggle), the caption strip explains the drop, and the
 * full blunder list anchors the bottom of the panel so the user can
 * jump between problem moves like a table of contents.
 */
export default function ReviewPlayer({
  gameId,
  intervalMs = 700,
  autoplay = true,
}: ReviewPlayerProps) {
  const t = useT();
  const [locale] = useLocale();
  const [game, setGame] = useState<GameDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [idx, setIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const activeId = useRef(gameId);

  // Per-move analyses — populated lazily when the user enters learn mode.
  // Once populated we don't drop them on mode toggle so flipping back to
  // learn after browsing in review feels instant.
  const [winratesBlack, setWinratesBlack] = useState<Record<number, number>>({});
  const [topMovesAt, setTopMovesAt] = useState<
    Record<number, { move: string; winrate: number; visits: number }[]>
  >({});
  const [coachingProgress, setCoachingProgress] = useState<{ done: number; total: number } | null>(null);
  // Have we ever entered learn mode for this game? Drives the analysis
  // lifecycle — once true, the pipeline runs to completion in the
  // background even if the user toggles back to review while it works.
  const [coachingStarted, setCoachingStarted] = useState(false);
  // Single source of truth for the coaching UX: review (clean replay)
  // vs learn (overlays + caption + blunder list all on together).
  const [mode, setMode] = useState<"review" | "learn">("review");

  const [soundOn, setSoundOn] = useState(true);
  useEffect(() => {
    setSoundOn(isStoneSoundEnabled());
  }, []);
  const toggleSound = () => {
    const next = !soundOn;
    setSoundOn(next);
    setStoneSoundEnabled(next);
  };

  const prevIdxRef = useRef(0);

  const inFlightRef = useRef(0);

  useEffect(() => {
    activeId.current = gameId;
    setGame(null);
    setError(null);
    setIdx(0);
    setPlaying(false);
    setWinratesBlack({});
    setTopMovesAt({});
    setCoachingStarted(false);
    setCoachingProgress(null);
    setMode("review");
    (async () => {
      try {
        const g = await api<GameDetail>(`/api/games/${gameId}`);
        if (activeId.current !== gameId) return;
        setGame(g);
        setIdx(0);
        setPlaying(autoplay);
      } catch {
        if (activeId.current !== gameId) return;
        setError("load_failed");
      }
    })();
  }, [gameId, autoplay]);

  // Analysis pipeline — runs once per game, kicked off when the user
  // first enters learn mode. Sequential per-move analyze with a
  // concurrency cap of 2 so the engine pool isn't starved.
  useEffect(() => {
    if (!coachingStarted || !game) return;
    let cancelled = false;
    const handicap = game.handicap ?? 0;
    const total = game.moves.length + 1;
    setCoachingProgress({ done: 0, total });

    const fetchOne = async (moveNum: number): Promise<void> => {
      while (inFlightRef.current >= 2) {
        await new Promise((r) => setTimeout(r, 50));
        if (cancelled) return;
      }
      inFlightRef.current += 1;
      try {
        const r = await api<AnalyzeResponse>(
          `/api/games/${gameId}/analyze?moveNum=${moveNum}`,
          { method: "POST" },
        );
        if (cancelled) return;
        const wrBlack = blackWinrateAt(r.winrate, moveNum, handicap);
        setWinratesBlack((prev) => ({ ...prev, [moveNum]: wrBlack }));
        setTopMovesAt((prev) => ({ ...prev, [moveNum]: r.top_moves }));
      } catch {
        // Single-move failure is non-fatal.
      } finally {
        inFlightRef.current = Math.max(0, inFlightRef.current - 1);
      }
    };

    (async () => {
      let done = 0;
      for (let n = 0; n < total; n++) {
        await fetchOne(n);
        if (cancelled) return;
        done += 1;
        setCoachingProgress({ done, total });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [coachingStarted, game, gameId]);

  useEffect(() => {
    if (!playing || !game) return;
    if (idx >= game.moves.length) { setPlaying(false); return; }
    const id = setInterval(() => {
      setIdx((i) => (game && i >= game.moves.length ? i : i + 1));
    }, intervalMs);
    return () => clearInterval(id);
  }, [playing, game, idx, intervalMs]);

  useEffect(() => {
    const prev = prevIdxRef.current;
    prevIdxRef.current = idx;
    if (!game || idx <= prev || idx <= 0) return;
    const m = game.moves[idx - 1];
    if (!m || m.is_undone || !m.coord || m.coord === "pass" || m.coord === "resign") return;
    playStoneClick();
  }, [idx, game]);

  const board = useMemo(
    () =>
      game
        ? replay(game.board_size, game.moves, idx, game.handicap ?? 0)
        : "",
    [game, idx],
  );
  const lastMove = useMemo(() => {
    if (!game || idx === 0) return null;
    const m = game.moves[idx - 1];
    if (!m || m.is_undone || !m.coord || m.coord === "pass" || m.coord === "resign")
      return null;
    const xy = gtpToXy(m.coord, game.board_size);
    return xy ? { x: xy[0], y: xy[1] } : null;
  }, [game, idx]);

  // Turning-point index — every move whose |winrate swing| exceeds the
  // threshold, regardless of direction. The sign distinguishes 패착
  // (the mover lost ground, d > 0) from 승착 (the mover gained, d < 0).
  // Populates progressively as analysis streams in.
  const turningPoints = useMemo(() => {
    if (mode !== "learn" || !game) return [] as { n: number; drop: number }[];
    const out: { n: number; drop: number }[] = [];
    for (let n = 1; n < game.moves.length + 1; n++) {
      const before = winratesBlack[n - 1];
      const after = winratesBlack[n];
      if (before === undefined || after === undefined) continue;
      const m = game.moves[n - 1];
      const d = moveDrop(before, after, m.color);
      if (Math.abs(d) > BLUNDER_THRESHOLD) out.push({ n, drop: d });
    }
    return out;
  }, [mode, game, winratesBlack]);

  // Mid-tier "주의 (noticeable)" swings — between SWING_NOTICE (3pp) and
  // BLUNDER_THRESHOLD (10pp). Painted as small gold dots on the scrubber
  // so the user gets a sense of swing density even outside the big
  // turning points.
  const noticeableSwings = useMemo(() => {
    if (mode !== "learn" || !game) return [] as { n: number; drop: number }[];
    const out: { n: number; drop: number }[] = [];
    for (let n = 1; n < game.moves.length + 1; n++) {
      const before = winratesBlack[n - 1];
      const after = winratesBlack[n];
      if (before === undefined || after === undefined) continue;
      const m = game.moves[n - 1];
      const d = moveDrop(before, after, m.color);
      const mag = Math.abs(d);
      if (mag >= 0.03 && mag <= BLUNDER_THRESHOLD) out.push({ n, drop: d });
    }
    return out;
  }, [mode, game, winratesBlack]);

  if (error) {
    return (
      <p className="text-sm text-oxblood p-4 text-center">
        {t("errors.game_not_found")}
      </p>
    );
  }
  if (!game) {
    return <p className="text-sm text-ink-mute p-4 text-center">…</p>;
  }

  const currentMove = idx > 0 ? game.moves[idx - 1] : null;
  const wrBefore =
    idx > 0 && idx - 1 in winratesBlack ? winratesBlack[idx - 1] : null;
  const wrAfter = idx in winratesBlack ? winratesBlack[idx] : null;
  const drop =
    currentMove && wrBefore !== null && wrAfter !== null
      ? moveDrop(wrBefore, wrAfter, currentMove.color)
      : null;
  const isBlunder = drop !== null && drop > BLUNDER_THRESHOLD;
  const isDecisive = drop !== null && drop < -BLUNDER_THRESHOLD;
  const isTurning = isBlunder || isDecisive;
  // Mid-tier swing: noticeable (3pp+) but not a true 승부처 (10pp+).
  // Shown in gold so users see it as "주의할 만한 변화"가 있었다는 시각 단서로.
  const SWING_NOTICE = 0.03;
  const isNoticeable =
    drop !== null && !isTurning && Math.abs(drop) >= SWING_NOTICE;
  const alternatives = idx > 0 ? topMovesAt[idx - 1] ?? [] : [];

  const learning = mode === "learn";
  const analysisDone =
    coachingProgress !== null &&
    coachingProgress.done >= coachingProgress.total;

  // Auto-overlay: in learn mode, whenever the current frame is a blunder
  // and we have alternatives data, paint KataGo's top three. No toggle.
  const altOverlay =
    learning && isBlunder && alternatives.length > 0
      ? alternatives
          .slice(0, 3)
          .map((m, i) => {
            const xy = gtpToXy(m.move, game.board_size);
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
              label: `${(m.winrate * 100).toFixed(0)}%`,
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

  const setLearnMode = () => {
    setMode("learn");
    if (!coachingStarted) setCoachingStarted(true);
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Mode toggle — single primary control. Clicking 학습 also kicks
          off analysis the first time, so there's nothing else to start. */}
      <div
        role="radiogroup"
        aria-label={t("review.modeLabel")}
        className="inline-flex self-start border border-ink-faint"
      >
        <button
          type="button"
          role="radio"
          aria-checked={mode === "review"}
          onClick={() => setMode("review")}
          className={
            "px-3 py-1.5 font-sans text-xs uppercase tracking-label transition-base " +
            (mode === "review"
              ? "bg-ink text-paper"
              : "text-ink-mute hover:text-ink")
          }
        >
          {t("review.modeReview")}
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={mode === "learn"}
          onClick={setLearnMode}
          className={
            "px-3 py-1.5 font-sans text-xs uppercase tracking-label transition-base border-l border-ink-faint flex items-center gap-2 " +
            (mode === "learn"
              ? "bg-oxblood text-paper"
              : "text-ink-mute hover:text-ink")
          }
        >
          <span>{t("review.modeLearn")}</span>
          {learning && coachingProgress && !analysisDone && (
            <span className="font-mono tabular-nums text-[10px]">
              {coachingProgress.done}/{coachingProgress.total}
            </span>
          )}
          {learning && analysisDone && (
            <span className="font-mono tabular-nums text-[10px]">
              {turningPoints.length}
              <span className="ml-0.5">●</span>
            </span>
          )}
        </button>
      </div>

      {/* Learn-mode status banner. Always visible while learning so the
          difference from review mode is obvious even before the first
          analysis result lands. */}
      {learning && (
        <div className="flex items-center gap-3 border border-oxblood bg-paper-deep px-3 py-2 font-sans text-xs">
          <span className="font-semibold uppercase tracking-label text-oxblood">
            {t("review.modeLearn")}
          </span>
          <span className="text-ink-mute">
            {!coachingProgress
              ? t("review.coachingProgress") + " 0 / —"
              : !analysisDone
              ? `${t("review.coachingProgress")} ${coachingProgress.done} / ${coachingProgress.total}`
              : `${t("review.coachingDone")} · ${turningPoints.length} ${t("review.turningPointTag")}`}
          </span>
          {analysisDone && wrAfter !== null && (
            <span className="ml-auto font-mono tabular-nums text-ink">
              {t("review.winrateBlackShort")} {(wrAfter * 100).toFixed(1)}%
            </span>
          )}
        </div>
      )}

      {/* Header row — left: scrubber position + current move marker.
          Right: 흑/백 식별 (돌 모양 + 닉네임). user_color로 사용자/AI 매칭. */}
      {(() => {
        const userIsBlack = (game.user_color ?? "black") === "black";
        const userRankSuffix = game.user_rank
          ? ` (${formatRank(game.user_rank, locale)})`
          : "";
        const userLabel = `${game.user_nickname ?? "—"}${userRankSuffix}`;
        const aiLabel = game.ai_player
          ? `${t(`game.players.${game.ai_player}.name`)}${
              game.ai_rank ? ` (${formatRank(game.ai_rank, locale)})` : ""
            }`
          : game.ai_rank
          ? formatRank(game.ai_rank, locale)
          : "AI";
        const blackName = userIsBlack ? userLabel : aiLabel;
        const whiteName = userIsBlack ? aiLabel : userLabel;
        return (
          <div className="flex flex-wrap items-baseline justify-between gap-2 font-mono text-xs text-ink-mute">
            <span className="tabular-nums">
              {idx} / {game.moves.length}
              {currentMove && (
                <span className="ml-2 text-ink">
                  {currentMove.color === "B" ? "●" : "○"}{" "}
                  <span className="tabular-nums">
                    {currentMove.coord ?? "pass"}
                  </span>
                </span>
              )}
            </span>
            <span className="flex items-baseline gap-2 text-ink">
              <span className="inline-flex items-baseline gap-1">
                <span className="text-ink">●</span>
                {userIsBlack && <CountryFlag code={game.user_country} />}
                <span className="font-sans text-xs">{blackName}</span>
              </span>
              <span className="text-ink-faint">vs</span>
              <span className="inline-flex items-baseline gap-1">
                <span className="text-ink">○</span>
                {!userIsBlack && <CountryFlag code={game.user_country} />}
                <span className="font-sans text-xs">{whiteName}</span>
              </span>
              {game.result && (
                <span className="text-ink-faint ml-1">· {game.result}</span>
              )}
            </span>
          </div>
        );
      })()}

      {/* Board frame: oxblood accent ring in learn mode so the user
          can tell at a glance which mode the panel is in. */}
      <div
        className={
          "w-full mx-auto " +
          (learning ? "ring-1 ring-oxblood ring-offset-2 ring-offset-paper" : "")
        }
      >
        <Board
          size={game.board_size}
          board={board}
          lastMove={lastMove}
          lastMoveKind={
            learning
              ? isBlunder
                ? "blunder"
                : isDecisive
                ? "decisive"
                : null
              : null
          }
          overlay={altOverlay}
        />
      </div>

      {/* Per-move caption — always when we have winrate data (regardless
          of mode). Color escalates by magnitude:
            < 3pp           → 회색 (소소한 변동)
            3–10pp          → gold (주의할 만한 swing)
            > 10pp 패착     → oxblood
            > 10pp 승착     → moss
      */}
      {currentMove && drop !== null && (
        <div
          className={
            "border px-3 py-2 font-sans text-sm flex flex-col gap-1 " +
            (isBlunder
              ? "border-oxblood text-oxblood bg-paper-deep"
              : isDecisive
              ? "border-moss text-moss bg-paper-deep"
              : isNoticeable
              ? "border-gold text-gold"
              : "border-ink-faint text-ink-mute")
          }
          aria-live="polite"
        >
          <div className="flex items-baseline justify-between gap-3">
            <span className="font-semibold tracking-label uppercase text-xs">
              {isBlunder
                ? t("review.blunderTag")
                : isDecisive
                ? t("review.decisiveTag")
                : t("review.coachTag")}
            </span>
            <span className="font-mono tabular-nums text-xs">
              {drop > 0 ? "−" : "+"}
              {Math.abs(drop * 100).toFixed(1)}%
            </span>
          </div>
          {isTurning && (
            <div className="font-sans text-xs leading-relaxed text-ink">
              {(() => {
                const sideKey = currentMove.color === "B" ? "review.sideBlack" : "review.sideWhite";
                const wrFrom =
                  wrBefore !== null
                    ? (currentMove.color === "B" ? wrBefore : 1 - wrBefore) * 100
                    : null;
                const wrTo =
                  wrAfter !== null
                    ? (currentMove.color === "B" ? wrAfter : 1 - wrAfter) * 100
                    : null;
                const best = alternatives[0];
                return (
                  <>
                    <span>{t(sideKey)} </span>
                    {wrFrom !== null && wrTo !== null && (
                      <span className="font-mono tabular-nums">
                        {wrFrom.toFixed(1)}% → {wrTo.toFixed(1)}%
                      </span>
                    )}
                    {isBlunder && best && (
                      <>
                        {" · "}
                        <span>{t("review.bestMove")} </span>
                        <span className="font-mono tabular-nums">{best.move}</span>
                      </>
                    )}
                  </>
                );
              })()}
            </div>
          )}
        </div>
      )}

      {/* Scrubber + blunder dots (only painted in learn mode) */}
      <div className="relative">
        <input
          type="range"
          min={0}
          max={game.moves.length}
          value={idx}
          onChange={(e) => { setIdx(Number(e.target.value)); setPlaying(false); }}
          className="w-full accent-oxblood block"
          aria-label={t("review.scrubber")}
        />
        {learning && (turningPoints.length > 0 || noticeableSwings.length > 0) && (
          <div
            aria-hidden="true"
            className="pointer-events-none absolute left-0 right-0 top-1/2 -translate-y-1/2 h-2"
          >
            {/* gold dots first (smaller) so oxblood / moss turning dots
                draw over them when the move qualifies as both — keeps the
                stronger signal visible. */}
            {noticeableSwings.map(({ n, drop: d }) => {
              const pct = (n / game.moves.length) * 100;
              return (
                <span
                  key={`n-${n}`}
                  className="absolute -translate-x-1/2 top-1/2 -translate-y-1/2 h-1 w-1 rounded-full bg-gold"
                  style={{ left: `${pct}%` }}
                  title={`#${n} ${(d > 0 ? "−" : "+") + Math.abs(d * 100).toFixed(1)}%`}
                />
              );
            })}
            {turningPoints.map(({ n, drop: d }) => {
              const pct = (n / game.moves.length) * 100;
              const kind = d > 0 ? "blunder" : "decisive";
              return (
                <span
                  key={n}
                  className={
                    "absolute -translate-x-1/2 h-2 w-2 rounded-full " +
                    (kind === "blunder" ? "bg-oxblood" : "bg-moss")
                  }
                  style={{ left: `${pct}%` }}
                  title={`#${n} ${kind === "blunder" ? t("review.blunderTag") : t("review.decisiveTag")}`}
                />
              );
            })}
          </div>
        )}
      </div>

      {/* Nav controls — always visible regardless of mode */}
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm"
          onClick={() => { setIdx(0); setPlaying(false); }}>
          {t("review.first")}
        </Button>
        <Button variant="outline" size="sm"
          onClick={() => { setIdx(Math.max(0, idx - 1)); setPlaying(false); }}>
          {t("review.prev")}
        </Button>
        <Button size="sm"
          onClick={() => {
            if (idx >= game.moves.length) setIdx(0);
            setPlaying((p) => !p);
          }}>
          {playing ? t("review.pause") : t("review.play")}
        </Button>
        <Button variant="outline" size="sm"
          onClick={() => { setIdx(Math.min(game.moves.length, idx + 1)); setPlaying(false); }}>
          {t("review.next")}
        </Button>
        <Button variant="outline" size="sm"
          onClick={() => { setIdx(game.moves.length); setPlaying(false); }}>
          {t("review.last")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={toggleSound}
          aria-pressed={soundOn}
          aria-label={soundOn ? t("review.soundOff") : t("review.soundOn")}
          className="ml-auto px-2"
          title={soundOn ? t("review.soundOff") : t("review.soundOn")}
        >
          {soundOn ? (
            <Volume2 size={16} strokeWidth={1.5} />
          ) : (
            <VolumeX size={16} strokeWidth={1.5} />
          )}
        </Button>
        <a
          href={`/api/games/${gameId}/sgf`}
          target="_blank"
          rel="noopener noreferrer"
          className="self-center font-sans text-xs font-semibold uppercase tracking-label text-oxblood hover:underline"
        >
          SGF
        </a>
      </div>

      {/* Turning-point list — 패착 (blunder) and 승착 (decisive) both
          surfaced as the analysis pipeline streams in. */}
      {learning && (
        <div className="border border-ink-faint divide-y divide-ink-faint">
          <div className="px-3 py-2 flex items-baseline justify-between font-sans text-xs">
            <span className="font-semibold uppercase tracking-label text-oxblood">
              {t("review.turningPointListTitle")}
            </span>
            <span className="font-mono tabular-nums text-ink-mute">
              {analysisDone ? turningPoints.length : "…"}
            </span>
          </div>
          {!analysisDone ? (
            <div className="px-3 py-2 font-sans text-xs text-ink-mute">
              {coachingProgress
                ? `${t("review.coachingProgress")} ${coachingProgress.done} / ${coachingProgress.total}`
                : t("review.coachingProgress") + "…"}
            </div>
          ) : turningPoints.length === 0 ? (
            <div className="px-3 py-2 font-sans text-xs text-ink-mute">
              {t("review.noTurningPointsFound")}
            </div>
          ) : (
            turningPoints.map(({ n, drop: d }) => {
              const m = game.moves[n - 1];
              const isCurrent = n === idx;
              const kind = d > 0 ? "blunder" : "decisive";
              const tone = kind === "blunder" ? "text-oxblood" : "text-moss";
              const label = kind === "blunder" ? t("review.blunderTag") : t("review.decisiveTag");
              return (
                <button
                  key={n}
                  type="button"
                  onClick={() => {
                    setIdx(n);
                    setPlaying(false);
                  }}
                  className={
                    "w-full text-left px-3 py-2 grid grid-cols-[auto_auto_auto_1fr_auto] gap-3 items-baseline font-sans text-sm hover:bg-paper-deep transition-base " +
                    (isCurrent ? "bg-paper-deep" : "")
                  }
                >
                  <span className="font-mono tabular-nums text-xs text-ink-mute">
                    #{n}
                  </span>
                  <span>{m.color === "B" ? "●" : "○"}</span>
                  <span className={"font-semibold tracking-label uppercase text-[10px] " + tone}>
                    {label}
                  </span>
                  <span className="font-mono tabular-nums text-xs">
                    {m.coord ?? "pass"}
                  </span>
                  <span className={"font-mono tabular-nums text-xs " + tone}>
                    {d > 0 ? "−" : "+"}{Math.abs(d * 100).toFixed(1)}%
                  </span>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

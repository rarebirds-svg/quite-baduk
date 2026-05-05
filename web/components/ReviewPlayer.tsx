"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Board from "@/components/Board";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { gtpToXy, handicapStonesFor, totalCells } from "@/lib/board";
import { Button } from "@/components/ui/button";

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
// No handicap: after even N, Black is to move (so wr_black = wr).
// Handicap H>0: B places H stones before move 1; first recorded move is W.
//   After N recorded moves with handicap, side-to-move parity flips —
//   B is to move when N is ODD.
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
// Positive = the moving side LOST winrate (= mistake). Threshold elsewhere.
function moveDrop(
  wrBlackBefore: number,
  wrBlackAfter: number,
  color: "B" | "W",
): number {
  return color === "B"
    ? wrBlackBefore - wrBlackAfter
    : wrBlackAfter - wrBlackBefore;
}

const BLUNDER_THRESHOLD = 0.10; // 10% winrate drop counts as a coaching note

function replay(
  size: number,
  moves: MoveEntryRaw[],
  upto: number,
  handicap = 0,
): string {
  const cells = Array.from({ length: totalCells(size) }, () => ".");
  // Pre-place handicap stones — they are part of the position from move 0
  // onward but never appear in the move log (the backend's rules engine
  // places them directly without recording MoveRow entries).
  for (const coord of handicapStonesFor(size, handicap)) {
    const xy = gtpToXy(coord, size);
    if (!xy) continue;
    const [x, y] = xy;
    cells[y * size + x] = "B";
  }
  for (let i = 0; i < Math.min(upto, moves.length); i++) {
    const m = moves[i];
    if (m.is_undone || !m.coord || m.coord === "pass") continue;
    const xy = gtpToXy(m.coord, size);
    if (!xy) continue;
    const [x, y] = xy;
    cells[y * size + x] = m.color;
  }
  return cells.join("");
}

export interface ReviewPlayerProps {
  gameId: number;
  /** Default ~700ms — compact modals feel better slightly faster. */
  intervalMs?: number;
  /** Auto-start playback on mount. Default true. */
  autoplay?: boolean;
}

/**
 * Self-contained kifu replay player. Fetches the game, renders the board,
 * and offers play/pause + scrubber + step controls. Designed to fit inside
 * dialogs / popups without pulling in the full review page's analysis UI.
 */
export default function ReviewPlayer({
  gameId,
  intervalMs = 700,
  autoplay = true,
}: ReviewPlayerProps) {
  const t = useT();
  const [game, setGame] = useState<GameDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [idx, setIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  // Track the current gameId to cancel a stale fetch if the caller swaps
  // games while one is in flight (clicking review on a different row).
  const activeId = useRef(gameId);
  // Per-move analyses, indexed by move position (0 = empty board, N = after
  // Nth move). Populated by the coaching pipeline below.
  const [winratesBlack, setWinratesBlack] = useState<Record<number, number>>({});
  const [topMovesAt, setTopMovesAt] = useState<
    Record<number, { move: string; winrate: number; visits: number }[]>
  >({});
  const [coachingActive, setCoachingActive] = useState(false);
  const [coachingProgress, setCoachingProgress] = useState<{ done: number; total: number } | null>(null);
  const [showAlternatives, setShowAlternatives] = useState(false);
  // Persistent "all blunders" panel that the user can toggle once analysis
  // is done. Stays open across move scrubs so the user can jump between
  // problem moves; alternatives overlay is opened per-move from the panel
  // itself or via the inline caption.
  const [showAllBlunders, setShowAllBlunders] = useState(false);
  // Concurrency cap: KataGo per-move analysis is not free. Even cached, the
  // first review of a long game would otherwise fire 200 requests at once.
  const inFlightRef = useRef(0);

  useEffect(() => {
    activeId.current = gameId;
    setGame(null);
    setError(null);
    setIdx(0);
    setPlaying(false);
    setWinratesBlack({});
    setTopMovesAt({});
    setCoachingActive(false);
    setCoachingProgress(null);
    setShowAlternatives(false);
    setShowAllBlunders(false);
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

  // Coaching pipeline — sequential per-move analysis. Opt-in via the
  // "코칭 시작" button so we don't surprise the user with engine load on
  // every review open. Results land in `winratesBlack` keyed by move index.
  useEffect(() => {
    if (!coachingActive || !game) return;
    let cancelled = false;
    const handicap = game.handicap ?? 0;
    const total = game.moves.length + 1; // positions 0..N
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
        // Single-move failure is non-fatal — skip and keep going.
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
  }, [coachingActive, game, gameId]);

  useEffect(() => {
    if (!playing || !game) return;
    if (idx >= game.moves.length) { setPlaying(false); return; }
    const id = setInterval(() => {
      setIdx((i) => (game && i >= game.moves.length ? i : i + 1));
    }, intervalMs);
    return () => clearInterval(id);
  }, [playing, game, idx, intervalMs]);

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

  // Blunder index list — computed unconditionally so the hook order is
  // stable across the early returns below.
  const blunderMoves = useMemo(() => {
    if (!coachingActive || !game) return [] as number[];
    const out: number[] = [];
    for (let n = 1; n < game.moves.length + 1; n++) {
      const before = winratesBlack[n - 1];
      const after = winratesBlack[n];
      if (before === undefined || after === undefined) continue;
      const m = game.moves[n - 1];
      const d = moveDrop(before, after, m.color);
      if (d > BLUNDER_THRESHOLD) out.push(n);
    }
    return out;
  }, [coachingActive, game, winratesBlack]);

  if (error) {
    return (
      <p className="text-sm text-oxblood p-4 text-center">
        {t("errors.game_not_found")}
      </p>
    );
  }
  if (!game) {
    return (
      <p className="text-sm text-ink-mute p-4 text-center">…</p>
    );
  }

  const currentMove = idx > 0 ? game.moves[idx - 1] : null;

  // Coaching read-outs for the move currently displayed (the one at idx).
  // wrBefore = winrate AT position idx-1 (before that move),
  // wrAfter = winrate AT position idx (after that move).
  const wrBefore =
    idx > 0 && idx - 1 in winratesBlack ? winratesBlack[idx - 1] : null;
  const wrAfter = idx in winratesBlack ? winratesBlack[idx] : null;
  const drop =
    currentMove && wrBefore !== null && wrAfter !== null
      ? moveDrop(wrBefore, wrAfter, currentMove.color)
      : null;
  const isBlunder = drop !== null && drop > BLUNDER_THRESHOLD;
  // Top moves at the position BEFORE the current move — i.e., the
  // alternatives that the moving player passed up.
  const alternatives = idx > 0 ? topMovesAt[idx - 1] ?? [] : [];

  // Render top alternatives as semi-transparent overlay markers. Reuses
  // the Board overlay shape (primary/secondary/tertiary).
  const altOverlay =
    showAlternatives && alternatives.length > 0
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

  // (blunderMoves computed earlier — hook order keeps it before any early returns.)

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between font-mono text-xs text-ink-mute">
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
          {wrAfter !== null && (
            <span className="ml-3 text-ink-mute">
              {t("review.winrateBlackShort")}: {(wrAfter * 100).toFixed(1)}%
            </span>
          )}
        </span>
        <span className="text-ink-faint">
          {game.user_nickname ?? "—"} · {game.ai_player ?? game.ai_rank ?? ""}
          {game.result ? ` · ${game.result}` : ""}
        </span>
      </div>

      <div className="max-w-[min(560px,100%)] mx-auto">
        <Board
          size={game.board_size}
          board={board}
          lastMove={lastMove}
          overlay={altOverlay}
        />
      </div>

      {currentMove && drop !== null && (
        <div
          className={
            "border px-3 py-2 font-sans text-sm flex items-baseline justify-between gap-3 " +
            (isBlunder
              ? "border-oxblood text-oxblood bg-paper-deep"
              : "border-ink-faint text-ink-mute")
          }
          aria-live="polite"
        >
          <span className="font-semibold tracking-label uppercase text-xs">
            {isBlunder ? t("review.blunderTag") : t("review.coachTag")}
          </span>
          <span className="font-mono tabular-nums text-xs">
            {drop > 0 ? "−" : "+"}
            {Math.abs(drop * 100).toFixed(1)}%
          </span>
          {alternatives.length > 0 && (
            <Button
              size="sm"
              variant="outline"
              className="ml-auto"
              onClick={() => setShowAlternatives((v) => !v)}
              aria-pressed={showAlternatives}
            >
              {showAlternatives ? t("review.hideAlt") : t("review.showAlt")}
            </Button>
          )}
        </div>
      )}

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
        {blunderMoves.length > 0 && (
          <div
            aria-hidden="true"
            className="pointer-events-none absolute left-0 right-0 top-1/2 -translate-y-1/2 h-2"
          >
            {blunderMoves.map((n) => {
              // Native range thumb has padding; matching exactly is tricky.
              // Use percentage along the track — close enough at typical
              // viewport widths.
              const pct = (n / game.moves.length) * 100;
              return (
                <span
                  key={n}
                  className="absolute -translate-x-1/2 h-2 w-2 rounded-full bg-oxblood"
                  style={{ left: `${pct}%` }}
                  title={`#${n} ${t("review.blunderTag")}`}
                />
              );
            })}
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3 -mt-1">
        {!coachingActive ? (
          <Button
            size="sm"
            variant="outline"
            className="text-oxblood border-oxblood"
            onClick={() => setCoachingActive(true)}
          >
            {t("review.startCoaching")}
          </Button>
        ) : coachingProgress && coachingProgress.done < coachingProgress.total ? (
          <span className="font-mono text-xs tabular-nums text-ink-mute">
            {t("review.coachingProgress")} {coachingProgress.done} /{" "}
            {coachingProgress.total}
          </span>
        ) : (
          <>
            <span className="font-sans text-xs uppercase tracking-label text-moss">
              {t("review.coachingDone")}
              {blunderMoves.length > 0 &&
                ` · ${blunderMoves.length} ${t("review.blunderCountSuffix")}`}
            </span>
            {/* Persistent access to the full coaching list. Stays visible
                regardless of whether the per-move alternatives are open. */}
            <Button
              size="sm"
              variant="outline"
              className="ml-auto text-oxblood border-oxblood"
              onClick={() => setShowAllBlunders((v) => !v)}
              aria-pressed={showAllBlunders}
              aria-controls="all-blunders-panel"
            >
              {showAllBlunders
                ? t("review.hideAllBlunders")
                : t("review.showAllBlunders")}
            </Button>
          </>
        )}
      </div>

      {coachingActive && showAllBlunders && (
        <div
          id="all-blunders-panel"
          className="border border-ink-faint divide-y divide-ink-faint"
        >
          {blunderMoves.length === 0 ? (
            <div className="px-3 py-2 font-sans text-xs text-ink-mute">
              {t("review.noBlundersFound")}
            </div>
          ) : (
            blunderMoves.map((n) => {
              const before = winratesBlack[n - 1];
              const after = winratesBlack[n];
              const m = game.moves[n - 1];
              const d = moveDrop(before, after, m.color);
              const isCurrent = n === idx;
              return (
                <button
                  key={n}
                  type="button"
                  onClick={() => {
                    setIdx(n);
                    setPlaying(false);
                    // Open alternatives for the move the user clicked
                    // through to so the panel feels like a navigator.
                    setShowAlternatives(true);
                  }}
                  className={
                    "w-full text-left px-3 py-2 grid grid-cols-[auto_auto_1fr_auto] gap-3 items-baseline font-sans text-sm hover:bg-paper-deep transition-base " +
                    (isCurrent ? "bg-paper-deep" : "")
                  }
                >
                  <span className="font-mono tabular-nums text-xs text-ink-mute">
                    #{n}
                  </span>
                  <span>{m.color === "B" ? "●" : "○"}</span>
                  <span className="font-mono tabular-nums text-xs">
                    {m.coord ?? "pass"}
                  </span>
                  <span className="font-mono tabular-nums text-xs text-oxblood">
                    −{(d * 100).toFixed(1)}%
                  </span>
                </button>
              );
            })
          )}
        </div>
      )}

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
        <a
          href={`/api/games/${gameId}/sgf`}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto self-center font-sans text-xs font-semibold uppercase tracking-label text-oxblood hover:underline"
        >
          SGF
        </a>
      </div>
    </div>
  );
}

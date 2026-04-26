"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Board from "@/components/Board";
import GameControls from "@/components/GameControls";
import AnalysisOverlay from "@/components/AnalysisOverlay";
import { openGameWS, type WSMessage, type GameWS, type ScoreResultMsg } from "@/lib/ws";
import { useGameStore, UNDO_LIMIT, emaWinrate } from "@/store/gameStore";
import { useAuthStore } from "@/store/authStore";
import { api } from "@/lib/api";
import { applyMoveWithCaptures, gtpToXy, xyToGtp } from "@/lib/board";
import { useT, useLocale } from "@/lib/i18n";
import { formatRank, type Rank } from "@/components/RankPicker";
import { playStoneClick } from "@/lib/soundfx";
import { PlayerCaption } from "@/components/editorial/PlayerCaption";
import { StatFigure } from "@/components/editorial/StatFigure";
import { DataBlock } from "@/components/editorial/DataBlock";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { WinrateBar } from "@/components/editorial/WinrateBar";
import BoardBgSwitcher from "@/components/BoardBgSwitcher";
import ReviewPlayer from "@/components/ReviewPlayer";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface GameMeta {
  board_size: number;
  user_color: "black" | "white";
  ai_rank: Rank;
  ai_style: string;
  ai_player: string | null;
  handicap: number;
}

export default function PlayPage() {
  const t = useT();
  const [locale] = useLocale();
  const params = useParams<{ id: string }>();
  const gameId = parseInt(params.id, 10);
  const g = useGameStore();
  const nickname = useAuthStore((s) => s.session?.nickname ?? null);
  const [meta, setMeta] = useState<GameMeta | null>(null);
  const wsRef = useRef<GameWS | null>(null);
  const preOptimisticBoard = useRef<string | null>(null);
  const optimisticUserMove = useRef<{ x: number; y: number } | null>(null);
  const [hint, setHint] =
    useState<{ move: string; winrate: number; visits: number }[]>([]);
  const [hintWinrate, setHintWinrate] = useState<number | null>(null);
  const [confirmResign, setConfirmResign] = useState(false);
  const [confirmPass, setConfirmPass] = useState(false);
  const [scoringDetail, setScoringDetail] =
    useState<ScoreResultMsg | null>(null);
  const [aiResigned, setAiResigned] = useState(false);
  const [kifuOpen, setKifuOpen] = useState(false);
  // Track the move_count we are optimistically anticipating. If the server
  // sends back a stale state (e.g. an initial handshake that arrived after
  // the user already clicked, or a reconnect mid-flight), we ignore its
  // board so the optimistic stone doesn't get wiped.
  const expectedMoveCount = useRef<number>(0);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api<GameMeta>(`/api/games/${gameId}`).then((detail) => {
      g.reset(detail.board_size);
      setMeta(detail);
    });

    const ws = openGameWS(gameId, (msg: WSMessage) => {
      if (msg.type === "state") {
        // An undo deliberately decreases move_count; a bumped undo_count
        // tells us the server accepted an undo so we drop the stale-move
        // filter for this payload.
        const isUndoResponse =
          typeof msg.undo_count === "number" && msg.undo_count > g.undoCount;
        // Discard the state if it's a *stale* view that would undo an
        // in-flight move — i.e. the server's move_count is behind what
        // we already expect. Only the error path rolls back optimistics.
        if (!isUndoResponse && msg.move_count < expectedMoveCount.current) {
          return;
        }
        preOptimisticBoard.current = null;
        expectedMoveCount.current = msg.move_count;
        // If the server's side-to-move equals our current side-to-move,
        // the full user+AI round trip has landed — drop the thinking
        // indicator defensively in case the ai_move message is lost or
        // arrives out of order.
        const roundComplete = msg.to_move === g.toMove;
        g.set({
          boardSize: msg.board_size,
          board: msg.board,
          toMove: msg.to_move,
          moveCount: msg.move_count,
          captures: msg.captures,
          error: null,
          ...(roundComplete ? { aiThinking: false } : {}),
          ...(typeof msg.winrate_black === "number"
            ? {
                winrateBlack: msg.winrate_black,
                winrateBlackSmoothed: emaWinrate(
                  g.winrateBlackSmoothed,
                  msg.winrate_black,
                ),
              }
            : {}),
          ...(typeof msg.score_lead_black === "number"
            ? { scoreLeadBlack: msg.score_lead_black }
            : {}),
          ...(typeof msg.endgame_phase === "boolean"
            ? { endgamePhase: msg.endgame_phase }
            : {}),
          ...(typeof msg.undo_count === "number"
            ? { undoCount: msg.undo_count }
            : {}),
          ...(isUndoResponse ? { lastAiMove: null, aiThinking: false } : {}),
        });
        setReady(true);
      } else if (msg.type === "winrate") {
        g.set({
          winrateBlack: msg.winrate_black,
          winrateBlackSmoothed: emaWinrate(
            g.winrateBlackSmoothed,
            msg.winrate_black,
          ),
          ...(typeof msg.score_lead_black === "number"
            ? { scoreLeadBlack: msg.score_lead_black }
            : {}),
        });
      } else if (msg.type === "ai_move") {
        const c = msg.coord?.toLowerCase();
        if (msg.coord && c !== "pass" && c !== "resign") playStoneClick();
        if (c === "pass") {
          toast(t("game.aiPassed"));
        }
        g.set({ lastAiMove: msg.coord, aiThinking: false });
      } else if (msg.type === "score_result") {
        setScoringDetail(msg);
      } else if (msg.type === "game_over") {
        g.set({ gameOver: true, result: msg.result, aiThinking: false });
        if (msg.reason === "ai_resigned") setAiResigned(true);
      } else if (msg.type === "error") {
        if (preOptimisticBoard.current !== null) {
          g.set({ board: preOptimisticBoard.current });
          preOptimisticBoard.current = null;
        }
        optimisticUserMove.current = null;
        // Clear the "last move" ring too — otherwise the red circle lingers
        // on the empty intersection the user just tried to click.
        g.set({ error: msg.code, aiThinking: false, lastAiMove: null });
        // Drop the optimistic advance so future state messages aren't
        // filtered out as stale.
        expectedMoveCount.current = g.moveCount;
        toast.error(t(`errors.${msg.code}`));
      }
    });
    wsRef.current = ws;
    return () => {
      ws.close();
      g.reset();
      setReady(false);
      setAiResigned(false);
      setScoringDetail(null);
      expectedMoveCount.current = 0;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameId]);

  const sendMove = (x: number, y: number) => {
    if (!ready || g.gameOver || g.aiThinking) return;
    const coord = xyToGtp(x, y, g.boardSize);
    const idx = y * g.boardSize + x;
    if (g.board[idx] !== ".") {
      g.set({ error: "OCCUPIED" });
      toast.error(t("errors.OCCUPIED"));
      return;
    }
    preOptimisticBoard.current = g.board;
    const userColor = g.toMove;
    // Resolve client-side captures so atari/catches vanish the instant the
    // user clicks — without this the captured stones linger on screen until
    // the server's authoritative state payload arrives.
    const newBoard = applyMoveWithCaptures(
      g.board,
      g.boardSize,
      x,
      y,
      userColor as "B" | "W",
    );
    optimisticUserMove.current = { x, y };
    // Reserve two move slots (user + AI) so a late initial-state payload
    // with a smaller move_count doesn't wipe the optimistic stone.
    expectedMoveCount.current = g.moveCount + 2;
    g.set({
      board: newBoard,
      aiThinking: true,
      error: null,
      lastAiMove: null,
    });
    setHint([]);
    setHintWinrate(null);
    playStoneClick();
    wsRef.current?.send({ type: "move", coord });
  };

  const pass = () => {
    // Confirmation dialog — if the AI passes in response, the game is
    // scored immediately. We want the user to think twice so they don't
    // accidentally end a game with yose plays still on the board.
    setConfirmPass(true);
  };
  const passConfirmed = () => {
    setConfirmPass(false);
    g.set({ aiThinking: true, error: null });
    wsRef.current?.send({ type: "pass" });
  };
  const undo = () => {
    if (g.undoCount >= UNDO_LIMIT) {
      toast.error(t("errors.UNDO_LIMIT_EXCEEDED"));
      return;
    }
    g.set({ error: null });
    wsRef.current?.send({ type: "undo", steps: 2 });
  };
  const requestScoring = () => {
    if (!g.endgamePhase) {
      toast.error(t("errors.NOT_IN_ENDGAME_PHASE"));
      return;
    }
    g.set({ error: null });
    wsRef.current?.send({ type: "score_request" });
  };
  const resign = async () => {
    setConfirmResign(false);
    try {
      await api(`/api/games/${gameId}/resign`, { method: "POST" });
      g.set({ gameOver: true });
    } catch {
      toast.error(t("errors.validation"));
    }
  };
  const hintMe = async () => {
    try {
      const r = await api<{
        hints: { move: string; winrate: number; visits: number }[];
        winrate?: number;
      }>(`/api/games/${gameId}/hint`, { method: "POST" });
      setHint(r.hints);
      setHintWinrate(
        typeof r.winrate === "number"
          ? r.winrate
          : r.hints[0]?.winrate ?? null
      );
    } catch {
      toast.error(t("errors.validation"));
    }
  };

  const lastMoveXy = useMemo(() => {
    if (g.lastAiMove) return gtpToXy(g.lastAiMove, g.boardSize);
    if (optimisticUserMove.current)
      return [optimisticUserMove.current.x, optimisticUserMove.current.y] as [
        number,
        number,
      ];
    return null;
  }, [g.lastAiMove, g.boardSize]);

  const overlay = useMemo(() => {
    return hint
      .slice(0, 3)
      .map((h, i) => {
        const xy = gtpToXy(h.move, g.boardSize);
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
          label: String(i + 1),
        };
      })
      .filter(
        (
          x
        ): x is {
          x: number;
          y: number;
          color: "primary" | "secondary" | "tertiary";
          label: string;
        } => x !== null
      );
  }, [hint, g.boardSize]);

  const territoryMarkers = scoringDetail
    ? {
        black: scoringDetail.black_points,
        white: scoringDetail.white_points,
        dame: scoringDetail.dame_points,
        deadStones: scoringDetail.dead_stones,
      }
    : undefined;

  return (
    <div className="flex flex-col gap-4 py-4 md:grid md:grid-cols-[minmax(0,1fr)_280px] md:gap-8">
      <div className="flex flex-col gap-4">
        <PlayerCaption
          color={meta?.user_color === "black" ? "white" : "black"}
          name={
            meta?.ai_player
              ? t(`game.players.${meta.ai_player}.name`)
              : "KataGo"
          }
          rank={
            meta
              ? `${formatRank(meta.ai_rank, locale)} · ${t(`game.aiStyleName.${meta.ai_style}`)}`
              : t("game.aiRank")
          }
          subtitle={g.aiThinking ? t("game.thinking") : ""}
        />
        <Board
          size={g.boardSize}
          board={g.board}
          lastMove={
            lastMoveXy ? { x: lastMoveXy[0], y: lastMoveXy[1] } : null
          }
          onClick={sendMove}
          disabled={!ready || g.aiThinking || g.gameOver}
          overlay={overlay}
          territoryMarkers={territoryMarkers}
        />
        <PlayerCaption
          color={meta?.user_color === "white" ? "white" : "black"}
          name={nickname ?? t("game.you")}
          rank={t("game.yourRank")}
          subtitle={
            (meta?.user_color === "white" ? g.toMove === "W" : g.toMove === "B") &&
            !g.gameOver &&
            !g.aiThinking
              ? t("game.yourTurn")
              : ""
          }
        />

        <GameControls
          onPass={pass}
          onResign={() => setConfirmResign(true)}
          onUndo={undo}
          onHint={hintMe}
          onScoreRequest={requestScoring}
          disabled={g.gameOver || g.aiThinking}
          undosRemaining={Math.max(0, UNDO_LIMIT - g.undoCount)}
          scoringAvailable={g.endgamePhase && !g.gameOver}
        />

        {g.gameOver && (
          <div className="border border-ink p-4 font-serif text-lg flex items-center">
            <span>{t("game.result")}: {g.result || ""}</span>
            <button
              type="button"
              className="ml-3 font-sans text-xs font-semibold uppercase tracking-label text-oxblood hover:underline"
              onClick={() => setKifuOpen(true)}
            >
              {t("game.viewKifu")}
            </button>
          </div>
        )}
      </div>

      <aside className="flex flex-col gap-6">
        {hint.length > 0 && hintWinrate !== null ? (
          <AnalysisOverlay topMoves={hint} winrate={hintWinrate} />
        ) : (
          <StatFigure value={g.moveCount} label={t("game.move")} />
        )}
        <RuleDivider label={t("game.winrate")} />
        <WinrateBar
          value={g.winrateBlackSmoothed ?? g.winrateBlack}
          blackLabel={t("game.winrateBlack")}
          whiteLabel={t("game.winrateWhite")}
        />
        {typeof g.scoreLeadBlack === "number" && (
          <div className="font-mono text-xs tabular-nums text-ink-mute text-center -mt-1">
            {(() => {
              const lead = g.scoreLeadBlack;
              if (Math.abs(lead) < 0.05) return t("game.evenPosition");
              const prefix = lead > 0 ? "B+" : "W+";
              return `${prefix}${Math.abs(lead).toFixed(1)}`;
            })()}
          </div>
        )}
        <RuleDivider label={t("game.info")} />
        <DataBlock
          label={t("game.captures")}
          value={`● ${g.captures?.B ?? 0}  ○ ${g.captures?.W ?? 0}`}
        />
        <DataBlock
          label={t("game.toMove")}
          value={g.toMove === "B" ? t("game.colorBlack") : t("game.colorWhite")}
        />
        <RuleDivider label={t("settings.boardBg")} />
        <BoardBgSwitcher compact />
      </aside>

      <Dialog open={confirmPass} onOpenChange={setConfirmPass}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("game.confirmPassTitle")}</DialogTitle>
            <DialogDescription>
              {t("game.confirmPassDesc")}
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirmPass(false)}>
              {t("game.cancel")}
            </Button>
            <Button onClick={passConfirmed}>
              {t("game.pass")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={confirmResign} onOpenChange={setConfirmResign}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("game.confirmResignTitle")}</DialogTitle>
            <DialogDescription>
              {t("game.confirmResignDesc")}
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirmResign(false)}>
              {t("game.cancel")}
            </Button>
            <Button variant="destructive" onClick={resign}>
              {t("game.resign")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog
        open={aiResigned}
        onOpenChange={(open) => {
          if (!open) setAiResigned(false);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("game.aiResignedTitle")}</DialogTitle>
            <DialogDescription className="font-serif text-xl text-ink">
              {t("game.aiResignedBody")}
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end">
            <Button onClick={() => setAiResigned(false)}>
              {t("game.confirm")}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Sheet
        open={scoringDetail !== null}
        onOpenChange={(open) => {
          if (!open) setScoringDetail(null);
        }}
      >
        <SheetContent
          side="right"
          className="w-full sm:max-w-sm"
        >
          <div className="flex flex-col gap-1 mb-2">
            <h2 className="font-serif text-lg font-semibold text-ink">
              {scoringDetail?.reason === "ai_passed"
                ? t("game.aiPassedScoredTitle")
                : t("game.scoringBreakdown")}
            </h2>
            <p className="font-serif text-2xl text-ink">
              {scoringDetail?.result ?? ""}
            </p>
          </div>
          {scoringDetail && (
            <div className="flex flex-col gap-3 font-mono tabular-nums text-sm mt-4">
              <div className="grid grid-cols-3 gap-2 border-b border-ink-faint pb-2">
                <span className="text-ink-mute">{t("game.blackTerritory")}</span>
                <span className="text-right">{scoringDetail.black_territory}</span>
                <span className="text-right text-ink-mute">
                  +{scoringDetail.black_captures} {t("game.blackCaptures")}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 border-b border-ink-faint pb-2">
                <span className="text-ink-mute">{t("game.whiteTerritory")}</span>
                <span className="text-right">{scoringDetail.white_territory}</span>
                <span className="text-right text-ink-mute">
                  +{scoringDetail.white_captures} {t("game.whiteCaptures")}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 border-b border-ink-faint pb-2">
                <span className="text-ink-mute">{t("game.komiLabel")}</span>
                <span />
                <span className="text-right">+{scoringDetail.komi}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 font-semibold">
                <span>{t("game.totalLabel")}</span>
                <span className="text-right">● {scoringDetail.black_score}</span>
                <span className="text-right">○ {scoringDetail.white_score}</span>
              </div>
            </div>
          )}
          <div className="flex justify-end mt-6">
            <Button onClick={() => setScoringDetail(null)}>
              {t("game.cancel")}
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      <Dialog
        open={kifuOpen}
        onOpenChange={(open) => {
          if (!open) setKifuOpen(false);
        }}
      >
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>{t("game.kifuDialogTitle")}</DialogTitle>
          </DialogHeader>
          {kifuOpen && <ReviewPlayer gameId={gameId} />}
        </DialogContent>
      </Dialog>
    </div>
  );
}

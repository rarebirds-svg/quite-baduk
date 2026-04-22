"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Board from "@/components/Board";
import GameControls from "@/components/GameControls";
import AnalysisOverlay from "@/components/AnalysisOverlay";
import { openGameWS, type WSMessage, type GameWS } from "@/lib/ws";
import { useGameStore } from "@/store/gameStore";
import { api } from "@/lib/api";
import { gtpToXy, xyToGtp } from "@/lib/board";
import { useT } from "@/lib/i18n";
import { playStoneClick } from "@/lib/soundfx";
import { PlayerCaption } from "@/components/editorial/PlayerCaption";
import { StatFigure } from "@/components/editorial/StatFigure";
import { DataBlock } from "@/components/editorial/DataBlock";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { WinrateBar } from "@/components/editorial/WinrateBar";
import BoardBgSwitcher from "@/components/BoardBgSwitcher";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function PlayPage() {
  const t = useT();
  const params = useParams<{ id: string }>();
  const gameId = parseInt(params.id, 10);
  const g = useGameStore();
  const wsRef = useRef<GameWS | null>(null);
  const preOptimisticBoard = useRef<string | null>(null);
  const optimisticUserMove = useRef<{ x: number; y: number } | null>(null);
  const [hint, setHint] =
    useState<{ move: string; winrate: number; visits: number }[]>([]);
  const [hintWinrate, setHintWinrate] = useState<number | null>(null);
  const [confirmResign, setConfirmResign] = useState(false);
  // Track the move_count we are optimistically anticipating. If the server
  // sends back a stale state (e.g. an initial handshake that arrived after
  // the user already clicked, or a reconnect mid-flight), we ignore its
  // board so the optimistic stone doesn't get wiped.
  const expectedMoveCount = useRef<number>(0);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api<{ board_size: number }>(`/api/games/${gameId}`).then((detail) => {
      g.reset(detail.board_size);
    });

    const ws = openGameWS(gameId, (msg: WSMessage) => {
      if (msg.type === "state") {
        // Discard the state if it's a *stale* view that would undo an
        // in-flight move — i.e. the server's move_count is behind what
        // we already expect. Only the error path rolls back optimistics.
        if (msg.move_count < expectedMoveCount.current) {
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
            ? { winrateBlack: msg.winrate_black }
            : {}),
        });
        setReady(true);
      } else if (msg.type === "winrate") {
        g.set({ winrateBlack: msg.winrate_black });
      } else if (msg.type === "ai_move") {
        const c = msg.coord?.toLowerCase();
        if (msg.coord && c !== "pass" && c !== "resign") playStoneClick();
        g.set({ lastAiMove: msg.coord, aiThinking: false });
      } else if (msg.type === "game_over") {
        g.set({ gameOver: true, result: msg.result, aiThinking: false });
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
    const newBoard =
      g.board.substring(0, idx) + userColor + g.board.substring(idx + 1);
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
    g.set({ aiThinking: true, error: null });
    wsRef.current?.send({ type: "pass" });
  };
  const undo = () => {
    g.set({ error: null });
    wsRef.current?.send({ type: "undo", steps: 2 });
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

  return (
    <div className="flex flex-col gap-4 py-4 md:grid md:grid-cols-[minmax(0,1fr)_280px] md:gap-8">
      <div className="flex flex-col gap-4">
        <PlayerCaption
          color="white"
          name="KataGo"
          rank={t("game.aiRank")}
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
        />
        <PlayerCaption
          color="black"
          name={t("game.you")}
          rank={t("game.yourRank")}
          subtitle={
            g.toMove === "B" && !g.gameOver && !g.aiThinking
              ? t("game.yourTurn")
              : ""
          }
        />

        <GameControls
          onPass={pass}
          onResign={() => setConfirmResign(true)}
          onUndo={undo}
          onHint={hintMe}
          disabled={g.gameOver || g.aiThinking}
        />

        {g.gameOver && (
          <div className="border border-ink p-4 font-serif text-lg">
            {t("game.result")}: {g.result || ""}{" "}
            <a
              className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood hover:underline ml-3"
              href={`/api/games/${gameId}/sgf`}
              target="_blank"
              rel="noreferrer"
            >
              {t("game.downloadSgf")}
            </a>
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
          value={g.winrateBlack}
          blackLabel={t("game.winrateBlack")}
          whiteLabel={t("game.winrateWhite")}
        />
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
    </div>
  );
}

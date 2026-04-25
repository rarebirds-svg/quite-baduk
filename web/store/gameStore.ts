"use client";
import { create } from "zustand";
import { totalCells } from "@/lib/board";

interface GameStoreState {
  boardSize: number;
  board: string;
  toMove: string;
  moveCount: number;
  captures: Record<string, number>;
  lastAiMove: string | null;
  aiThinking: boolean;
  gameOver: boolean;
  result: string | null;
  error: string | null;
  winrateBlack: number | null;
  // Exponentially-smoothed version of winrateBlack for the UI bar, so the
  // display doesn't jitter every time a 32-visit read shifts 10+ points.
  // Internal decisions (AI resign, endgame phase) still use the raw
  // server value; only the visual indicator reads the smoothed value.
  winrateBlackSmoothed: number | null;
  scoreLeadBlack: number | null;
  endgamePhase: boolean;
  undoCount: number;
  set(partial: Partial<GameStoreState>): void;
  reset(size?: number): void;
}

function initial(size: number) {
  return {
    boardSize: size,
    board: ".".repeat(totalCells(size)),
    toMove: "B",
    moveCount: 0,
    captures: { B: 0, W: 0 },
    lastAiMove: null as string | null,
    aiThinking: false,
    gameOver: false,
    result: null as string | null,
    error: null as string | null,
    winrateBlack: null as number | null,
    winrateBlackSmoothed: null as number | null,
    scoreLeadBlack: null as number | null,
    endgamePhase: false,
    undoCount: 0,
  };
}

export const UNDO_LIMIT = 3;

// EMA coefficient for the displayed winrate. Lower = smoother (more lag).
// 0.35 keeps responsiveness for real changes while damping single-read
// noise of the 32-visit mid-game analysis.
export const WINRATE_EMA_ALPHA = 0.35;

/** Fold a fresh winrate sample into the EMA. Null raw → null (no display). */
export function emaWinrate(prev: number | null, next: number | null): number {
  if (next === null || next === undefined) {
    return prev ?? 0.5;
  }
  if (prev === null || prev === undefined) return next;
  return prev * (1 - WINRATE_EMA_ALPHA) + next * WINRATE_EMA_ALPHA;
}

export const useGameStore = create<GameStoreState>((set) => ({
  ...initial(19),
  set: (p) => set(p),
  reset: (size = 19) => set(initial(size)),
}));

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
  };
}

export const useGameStore = create<GameStoreState>((set) => ({
  ...initial(19),
  set: (p) => set(p),
  reset: (size = 19) => set(initial(size)),
}));

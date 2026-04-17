"use client";
import { create } from "zustand";

interface GameState {
  board: string;           // 361 chars
  toMove: string;          // "B" | "W"
  moveCount: number;
  captures: Record<string, number>;
  lastAiMove: string | null;
  aiThinking: boolean;
  gameOver: boolean;
  result: string | null;
  error: string | null;
  set(partial: Partial<GameState>): void;
  reset(): void;
}

const initial = {
  board: ".".repeat(19 * 19),
  toMove: "B",
  moveCount: 0,
  captures: { B: 0, W: 0 },
  lastAiMove: null as string | null,
  aiThinking: false,
  gameOver: false,
  result: null as string | null,
  error: null as string | null
};

export const useGameStore = create<GameState>((set) => ({
  ...initial,
  set: (p) => set(p),
  reset: () => set(initial)
}));

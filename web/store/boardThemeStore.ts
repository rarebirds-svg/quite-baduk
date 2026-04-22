"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type BoardTheme = "paper" | "wood" | "slate" | "kaya";

export const BOARD_THEMES: Record<
  BoardTheme,
  { bg: string; lineInk: string; starInk: string; labelInk: string }
> = {
  paper: {
    bg: "rgb(233 223 201)",
    lineInk: "rgb(26 23 21)",
    starInk: "rgb(26 23 21)",
    labelInk: "rgb(107 99 90)",
  },
  wood: {
    bg: "rgb(216 180 120)",
    lineInk: "rgb(40 28 18)",
    starInk: "rgb(40 28 18)",
    labelInk: "rgb(82 62 40)",
  },
  kaya: {
    bg: "rgb(224 174 105)",
    lineInk: "rgb(44 28 14)",
    starInk: "rgb(44 28 14)",
    labelInk: "rgb(92 62 32)",
  },
  slate: {
    bg: "rgb(72 82 92)",
    lineInk: "rgb(222 228 235)",
    starInk: "rgb(222 228 235)",
    labelInk: "rgb(176 186 196)",
  },
};

interface S {
  theme: BoardTheme;
  setTheme: (t: BoardTheme) => void;
}

export const useBoardTheme = create<S>()(
  persist(
    (set) => ({
      theme: "paper",
      setTheme: (t) => set({ theme: t }),
    }),
    { name: "board_theme" }
  )
);

"use client";
// 착수 방식(한 번에 착수 / 터치 후 확인) 선호를 localStorage에 영속하는 store.
// 기본값 auto — 터치 기기(pointer: coarse)에서만 확인 단계를 둔다.
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type MoveConfirmPref = "auto" | "tap" | "confirm";

interface S {
  moveConfirm: MoveConfirmPref;
  setMoveConfirm: (m: MoveConfirmPref) => void;
}

export const useMovePref = create<S>()(
  persist(
    (set) => ({
      moveConfirm: "auto",
      setMoveConfirm: (m) => set({ moveConfirm: m }),
    }),
    { name: "move_confirm" }
  )
);

/** 선호값을 실제 동작(확인 단계 사용 여부)으로 푼다. auto는 터치 기기 여부로 결정. */
export function resolveMoveConfirm(pref: MoveConfirmPref): boolean {
  if (pref === "confirm") return true;
  if (pref === "tap") return false;
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(pointer: coarse)").matches;
}

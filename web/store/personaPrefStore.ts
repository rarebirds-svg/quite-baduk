"use client";
// 레전드 기사 인트로·코멘트 표시 여부를 localStorage에 영속하는 store.
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface S {
  commentary: boolean;
  setCommentary: (on: boolean) => void;
}

export const usePersonaPref = create<S>()(
  persist(
    (set) => ({
      commentary: true,
      setCommentary: (on) => set({ commentary: on }),
    }),
    { name: "persona_commentary" }
  )
);

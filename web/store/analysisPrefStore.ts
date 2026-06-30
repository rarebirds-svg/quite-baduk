"use client";
// 형세 정보 표시 밀도(초보/분석가) 선호를 localStorage에 영속하는 store
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type AnalysisDensity = "beginner" | "analyst";

interface S {
  density: AnalysisDensity;
  setDensity: (d: AnalysisDensity) => void;
}

export const useAnalysisPref = create<S>()(
  persist(
    (set) => ({
      // analyst 기본 — 기존 사용자의 승률 상시 노출 동작을 보존한다.
      // 입문자는 beginner로 전환해 형세 정보를 숨길 수 있다.
      density: "analyst",
      setDensity: (d) => set({ density: d }),
    }),
    { name: "analysis_density" }
  )
);

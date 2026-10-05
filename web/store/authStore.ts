"use client";
import { create } from "zustand";

export interface LinkedAccount { provider: string; email?: string | null }
export interface Session {
  id: number;
  nickname: string;
  token?: string | null;
  // 옵트인으로 연동한 외부 계정. 없으면 순수 닉네임 세션.
  account?: LinkedAccount | null;
}

interface AuthState {
  session: Session | null;
  isAdmin: boolean;
  setSession(s: Session | null): void;
  setIsAdmin(v: boolean): void;
}

export const useAuthStore = create<AuthState>((set) => ({
  session: null,
  isAdmin: false,
  setSession: (s) => set({ session: s, ...(s === null ? { isAdmin: false } : {}) }),
  setIsAdmin: (v) => set({ isAdmin: v }),
}));

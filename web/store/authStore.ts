"use client";
import { create } from "zustand";

export interface Session { id: number; nickname: string; }

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

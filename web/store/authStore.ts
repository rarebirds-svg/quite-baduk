"use client";
import { create } from "zustand";

export interface Session { id: number; nickname: string; }

interface AuthState {
  session: Session | null;
  setSession(s: Session | null): void;
}

export const useAuthStore = create<AuthState>((set) => ({
  session: null,
  setSession: (s) => set({ session: s })
}));

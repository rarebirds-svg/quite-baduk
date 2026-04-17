"use client";
import { create } from "zustand";

export interface User { id: number; email: string; display_name: string; preferred_rank?: string | null; locale?: string; theme?: string; }

interface AuthState {
  user: User | null;
  setUser(u: User | null): void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  setUser: (u) => set({ user: u })
}));

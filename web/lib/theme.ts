"use client";
export type Theme = "light" | "dark";
export function getTheme(): Theme {
  if (typeof window === "undefined") return "light";
  const saved = localStorage.getItem("theme") as Theme | null;
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
export function setTheme(t: Theme) {
  localStorage.setItem("theme", t);
  document.documentElement.classList.toggle("dark", t === "dark");
}
export function applyTheme() {
  setTheme(getTheme());
}

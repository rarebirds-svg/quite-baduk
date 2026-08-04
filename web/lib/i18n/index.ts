"use client";
import ko from "./ko.json";
import { useSyncExternalStore } from "react";
import { translate, type Locale } from "./translate";

export type { Locale };

type Dict = typeof ko;
type NestedKey<T, P extends string = ""> =
  T extends object
    ? { [K in keyof T & string]: NestedKey<T[K], `${P}${P extends "" ? "" : "."}${K}`> }[keyof T & string]
    : P;

let currentLocale: Locale = "ko";
const listeners = new Set<() => void>();

function readLocale(): Locale {
  if (typeof window === "undefined") return "ko";
  const saved = (localStorage.getItem("locale") as Locale | null) || null;
  if (saved === "ko" || saved === "en") return saved;
  return (navigator.language?.startsWith("ko") ? "ko" : "en");
}

function notify() {
  listeners.forEach((l) => l());
}

export function setLocale(loc: Locale) {
  currentLocale = loc;
  if (typeof window !== "undefined") localStorage.setItem("locale", loc);
  notify();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return currentLocale;
}

function getServerSnapshot() {
  return "ko" as Locale;
}

export function useLocale(): [Locale, (l: Locale) => void] {
  const loc = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  return [loc, setLocale];
}

export function initLocale() {
  if (typeof window === "undefined") return;
  currentLocale = readLocale();
  document.documentElement.lang = currentLocale;
}

export function t(key: string, params: Record<string, string | number> = {}): string {
  return translate(currentLocale, key, params);
}

export function useT() {
  useLocale(); // subscribe so re-renders happen on locale change
  return t;
}

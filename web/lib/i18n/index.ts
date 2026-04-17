"use client";
import ko from "./ko.json";
import en from "./en.json";
import { useSyncExternalStore } from "react";

export type Locale = "ko" | "en";
const dicts = { ko, en } as const;

type Dict = typeof ko;
type NestedKey<T, P extends string = ""> =
  T extends object
    ? { [K in keyof T & string]: NestedKey<T[K], `${P}${P extends "" ? "" : "."}${K}`> }[keyof T & string]
    : P;

function getFromPath(obj: unknown, path: string): unknown {
  return path.split(".").reduce((acc: unknown, k: string) => {
    if (acc && typeof acc === "object" && k in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[k];
    }
    return null;
  }, obj);
}

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
  const dict = dicts[currentLocale];
  const raw = getFromPath(dict, key);
  if (typeof raw !== "string") return key;
  let value: string = raw;
  for (const [k, v] of Object.entries(params)) {
    value = value.replace(`{${k}}`, String(v));
  }
  return value;
}

export function useT() {
  useLocale(); // subscribe so re-renders happen on locale change
  return t;
}

"use client";
import en from "./en.json";
import ja from "./ja.json";
import ko from "./ko.json";
import zh from "./zh.json";
import { useSyncExternalStore } from "react";

export type Locale = "ko" | "en" | "ja" | "zh";
export const SUPPORTED_LOCALES: readonly Locale[] = ["ko", "en", "ja", "zh"] as const;

// Display labels shown in the language picker. ASCII for "EN" so the toggle
// reads like a button across all four scripts.
export const LOCALE_LABELS: Record<Locale, string> = {
  ko: "한국어",
  en: "English",
  ja: "日本語",
  zh: "中文",
};

const dicts = { ko, en, ja, zh } as const;

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
  const saved = localStorage.getItem("locale");
  if (saved && (SUPPORTED_LOCALES as readonly string[]).includes(saved)) {
    return saved as Locale;
  }
  // Auto-detect from the browser language. Match the prefix so e.g.
  // "zh-CN", "zh-TW", "zh-Hant" all map to "zh"; "ja-JP" → "ja"; etc.
  const navLang = (typeof navigator !== "undefined" ? navigator.language : "") || "";
  for (const loc of SUPPORTED_LOCALES) {
    if (navLang.toLowerCase().startsWith(loc)) return loc;
  }
  return "en";
}

function notify() {
  listeners.forEach((l) => l());
}

export function setLocale(loc: Locale) {
  currentLocale = loc;
  if (typeof window !== "undefined") {
    localStorage.setItem("locale", loc);
    document.documentElement.lang = loc;
  }
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
  if (typeof raw !== "string") {
    // Fallback: try English so a missing locale-specific key never shows the
    // raw key in production. (Matches every other major i18n library.)
    if (currentLocale !== "en") {
      const fallback = getFromPath(dicts.en, key);
      if (typeof fallback === "string") {
        let v = fallback;
        for (const [k, val] of Object.entries(params)) {
          v = v.replace(`{${k}}`, String(val));
        }
        return v;
      }
    }
    return key;
  }
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

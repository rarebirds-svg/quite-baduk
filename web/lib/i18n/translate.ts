// 로케일을 인자로 받는 순수 번역 함수 — "use client" 경계에 묶이지 않아 서버 컴포넌트에서도 호출할 수 있다.
import ko from "./ko.json";
import en from "./en.json";

export type Locale = "ko" | "en";

const dicts = { ko, en } as const;

function getFromPath(obj: unknown, path: string): unknown {
  return path.split(".").reduce((acc: unknown, k: string) => {
    if (acc && typeof acc === "object" && k in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[k];
    }
    return null;
  }, obj);
}

export function translate(
  locale: Locale,
  key: string,
  params: Record<string, string | number> = {},
): string {
  const raw = getFromPath(dicts[locale], key);
  if (typeof raw !== "string") return key;
  let value: string = raw;
  for (const [k, v] of Object.entries(params)) {
    value = value.replace(`{${k}}`, String(v));
  }
  return value;
}

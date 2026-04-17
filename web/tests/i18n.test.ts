import { describe, it, expect } from "vitest";
import ko from "@/lib/i18n/ko.json";
import en from "@/lib/i18n/en.json";

function collectKeys(obj: unknown, prefix = ""): string[] {
  return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) => {
    const path = prefix ? `${prefix}.${k}` : k;
    return typeof v === "object" && v !== null ? collectKeys(v, path) : [path];
  });
}

describe("i18n", () => {
  it("ko and en have identical keys", () => {
    const koKeys = collectKeys(ko).sort();
    const enKeys = collectKeys(en).sort();
    expect(koKeys).toEqual(enKeys);
  });
});

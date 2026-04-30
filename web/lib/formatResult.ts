import { type Locale, t } from "@/lib/i18n";

/**
 * Convert an SGF-style game result ("W+50.4", "B+R", …) into a sentence
 * a casual reader can parse without knowing Go notation.
 *
 * Inputs we expect from the backend:
 *   "B+R" / "W+R"      — wins by resignation (불계승)
 *   "B+12.5" / "W+50.4" — wins by N points (집 차)
 *   ""  / null         — game still in progress
 *   anything else      — passed through unchanged so we never lose info
 */
export function formatGameResult(raw: string | null | undefined): string {
  if (!raw) return "";
  const m = /^([BW])\+(.+)$/i.exec(raw.trim());
  if (!m) return raw;

  const colorKey = m[1].toUpperCase() === "B" ? "game.colorBlack" : "game.colorWhite";
  const color = t(colorKey);
  const tail = m[2].trim();

  if (/^R$/i.test(tail)) {
    // 불계승 / Win by resignation
    return t("game.result.byResignation", { color });
  }
  if (/^T$/i.test(tail)) {
    // Time loss — not produced today, but reserved for forward-compat.
    return t("game.result.byTimeout", { color });
  }
  // Numeric margin — keep the number verbatim so we don't round the half-point.
  const margin = tail.replace(/[^0-9.]/g, "");
  if (margin) {
    return t("game.result.byPoints", { color, points: margin });
  }
  return raw;
}

// `Locale` is re-exported so call sites can keep their import surface tidy.
export type { Locale };

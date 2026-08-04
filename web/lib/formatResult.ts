// SGF 결과 표기("W+50.4", "B+R")를 화면에 그대로 쓸 수 있는 한 문장으로 바꾼다.
import { t } from "@/lib/i18n";

/**
 * "W+50.4" → "백 50.4집 승", "B+R" → "흑 불계승".
 *
 * 인식하지 못한 표기는 원본을 그대로 돌려준다 — 백엔드가 새 형식을 내보내도
 * 화면에서 정보가 사라지지 않게 하기 위함이다.
 */
export function formatGameResult(raw: string | null | undefined): string {
  if (!raw) return "";

  const match = /^([BW])\+(.+)$/i.exec(raw.trim());
  if (!match) return raw;

  const color = t(match[1].toUpperCase() === "B" ? "game.colorBlack" : "game.colorWhite");
  const margin = match[2].trim();

  if (/^R$/i.test(margin)) return t("game.resultText.byResignation", { color });
  // 반집(0.5)이 살아야 하므로 숫자를 문자열 그대로 넘긴다.
  if (/^\d+(\.\d+)?$/.test(margin)) return t("game.resultText.byPoints", { color, points: margin });

  return raw;
}

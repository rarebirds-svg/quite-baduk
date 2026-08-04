// SGF 결과 표기("W+50.4", "B+R", "Jigo")를 화면에 그대로 쓸 수 있는 한 문장으로 바꾼다.
import { translate, type Locale } from "@/lib/i18n/translate";

// 승자가 없는 단독 표기. pro_games 실제 분포에 있는 값만 담는다.
const STANDALONE: Record<string, string> = {
  jigo: "game.resultText.draw",
  unfinished: "game.resultText.unfinished",
  void: "game.resultText.void",
  unknown: "game.resultText.unknown",
};

// "B+" 뒤에 오는 승인(勝因) 표기. 프로 기보는 R/Resign을 섞어 쓴다.
const REASON: Record<string, string> = {
  r: "game.resultText.byResignation",
  resign: "game.resultText.byResignation",
  t: "game.resultText.byTime",
  f: "game.resultText.byForfeit",
};

/**
 * "W+50.4" → "백 50.4집 승", "B+R" → "흑 불계승", "Jigo" → "무승부".
 *
 * 인식하지 못한 표기는 원본을 그대로 돌려준다 — 백엔드나 새 기보 소스가
 * 낯선 형식을 내보내도 화면에서 정보가 사라지지 않게 하기 위함이다.
 *
 * `locale`을 인자로 받는 이유는 서버 컴포넌트(generateMetadata 등)에서도
 * 호출하기 때문이다. `lib/i18n`의 `t`는 "use client" 모듈이라 서버에서 부르면
 * 클라이언트 참조가 되어 호출 자체가 실패한다.
 */
export function formatGameResult(
  raw: string | null | undefined,
  locale: Locale = "ko",
): string {
  if (!raw) return "";

  const trimmed = raw.trim();
  const standalone = STANDALONE[trimmed.toLowerCase()];
  if (standalone) return translate(locale, standalone);

  const match = /^([BW])\+(.+)$/i.exec(trimmed);
  if (!match) return raw;

  const color = translate(
    locale,
    match[1].toUpperCase() === "B" ? "game.colorBlack" : "game.colorWhite",
  );
  const margin = match[2].trim();

  const reason = REASON[margin.toLowerCase()];
  if (reason) return translate(locale, reason, { color });
  // 반집(0.5)이 살아야 하므로 숫자를 파싱하지 않고 문자열 그대로 넘긴다.
  if (/^\d+(\.\d+)?$/.test(margin)) {
    return translate(locale, "game.resultText.byPoints", { color, points: margin });
  }

  return raw;
}

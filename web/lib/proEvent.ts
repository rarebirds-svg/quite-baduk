// 프로 기보 EV(기전)·RO(국수)를 로케일별 표기 문자열로 조립한다.
import { t, type Locale } from "@/lib/i18n";

// EV 이름 토큰(소문자) → i18n 기전 키.
const NAME_TO_KEY: Record<string, string> = {
  chunlan: "chunlan",
  fujitsu: "fujitsu",
  ing: "ing",
  lg: "lg",
  samsung: "samsung",
  toyota: "toyota",
};

const EVENT_RE = /^(?:(\d+)(?:st|nd|rd|th)\s+)?(.+?)\s+Cup(?:\s+(Final))?(?:,\s*(.+))?$/i;

interface ParsedEvent {
  editionNum?: number;
  tournamentKey?: string;
  stage?: "final" | "prelim";
}

function parseEvent(event: string): ParsedEvent {
  const m = EVENT_RE.exec(event.trim());
  if (!m) return {};
  const [, edition, name, finalWord, tail] = m;
  const key = NAME_TO_KEY[name.trim().toLowerCase()];
  let stage: "final" | "prelim" | undefined;
  if (tail && /prelim/i.test(tail)) stage = "prelim";
  else if (finalWord) stage = "final";
  return {
    editionNum: edition ? Number(edition) : undefined,
    tournamentKey: key,
    stage,
  };
}

// RO 원문에서 후행 정수(국수)를 뽑는다. "Final 2" → 2, "Final" → undefined.
function parseGameNo(round: string | null): number | undefined {
  if (!round) return undefined;
  const m = /(\d+)\s*$/.exec(round.trim());
  return m ? Number(m[1]) : undefined;
}

export function formatProEvent(
  event: string | null,
  round: string | null,
  locale: Locale,
): string {
  if (!event) return "";
  const { editionNum, tournamentKey, stage } = parseEvent(event);
  const gameNo = parseGameNo(round);

  // 미지 기전 — 원문을 살리고 국수만 로케일에 맞게 덧붙인다.
  if (!tournamentKey) {
    if (gameNo === undefined) return event;
    return locale === "ko"
      ? `${event} ${t("spectate.proGameNo", { n: gameNo })}`
      : `${event} · ${t("spectate.proGameNo", { n: gameNo })}`;
  }

  // 국수가 있으면 결승 best-of 시리즈를 함의 → stage 보강.
  const stageKey = stage ?? (gameNo !== undefined ? "final" : undefined);

  if (locale === "ko") {
    const parts = [
      editionNum !== undefined ? t("spectate.proEdition", { n: editionNum }) : null,
      t(`spectate.proTournament.${tournamentKey}`),
      stageKey ? t(`spectate.proStage.${stageKey}`) : null,
      gameNo !== undefined ? t("spectate.proGameNo", { n: gameNo }) : null,
    ].filter(Boolean);
    return parts.join(" ");
  }

  // en — 국제 표준 영문 원문 유지 + Game N.
  return gameNo === undefined
    ? event
    : `${event} · ${t("spectate.proGameNo", { n: gameNo })}`;
}

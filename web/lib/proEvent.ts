// 프로 기보 EV(기전)·RO(국수)를 로케일별 표기 문자열로 조립한다.
import { t, type Locale } from "@/lib/i18n";
import { TOURNAMENT_KO } from "@/lib/proLocale";

interface ParsedEvent {
  editionNum?: number;
  base: string;
  baseKo?: string;
  stage?: "final" | "prelim";
}

// "10th Chunlan Cup Final" / "Castle Game" / "Ing Cup, Korean preliminary" 등을 분해.
function parseEvent(event: string): ParsedEvent {
  let rest = event.trim();
  // 선행 서수
  let editionNum: number | undefined;
  const ord = /^(\d+)(?:st|nd|rd|th)\s+/i.exec(rest);
  if (ord) {
    editionNum = Number(ord[1]);
    rest = rest.slice(ord[0].length);
  }
  // 단계 분리
  let stage: "final" | "prelim" | undefined;
  const prelim = /,\s*[^,]*prelim[^,]*$/i.exec(rest);
  if (prelim) {
    stage = "prelim";
    rest = rest.slice(0, prelim.index);
  } else if (/\s+Final\b/i.test(rest)) {
    stage = "final";
    rest = rest.replace(/\s+Final\b.*$/i, "");
  } else {
    rest = rest.replace(/\s+Title\b.*$/i, "");
  }
  const base = rest.trim();
  return { editionNum, base, baseKo: TOURNAMENT_KO[base], stage };
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
  const { editionNum, baseKo, stage } = parseEvent(event);
  const gameNo = parseGameNo(round);

  // 미매핑 기전 — 원문 + 국수만 로케일 접미.
  if (locale !== "ko" || !baseKo) {
    if (gameNo === undefined) return event;
    return locale === "ko"
      ? `${event} ${t("spectate.proGameNo", { n: gameNo })}`
      : `${event} · ${t("spectate.proGameNo", { n: gameNo })}`;
  }

  // ko & 매핑 — 조립. 국수가 있으면 결승 시리즈 함의 → stage 보강.
  const stageKey = stage ?? (gameNo !== undefined ? "final" : undefined);
  const parts = [
    editionNum !== undefined ? t("spectate.proEdition", { n: editionNum }) : null,
    baseKo,
    stageKey ? t(`spectate.proStage.${stageKey}`) : null,
    gameNo !== undefined ? t("spectate.proGameNo", { n: gameNo }) : null,
  ].filter(Boolean);
  return parts.join(" ");
}

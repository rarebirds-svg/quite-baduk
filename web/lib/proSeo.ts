// 프로 기보 상세 페이지의 SEO 제목·설명을 한글 기사명·기전명으로 조립한다(서버 안전).
import { formatGameResult } from "@/lib/formatResult";
import { translate, type Locale } from "@/lib/i18n/translate";
import { formatProEvent } from "@/lib/proEvent";
import { localizePlayer, localizeRank } from "@/lib/proLocale";

export interface ProSeoGame {
  id: number;
  black_player?: string | null;
  white_player?: string | null;
  black_rank?: string | null;
  white_rank?: string | null;
  event?: string | null;
  round?: string | null;
  game_date?: string | null;
  result?: string | null;
  board_size?: number;
  handicap?: number;
  komi?: number;
  move_count?: number;
}

function names(g: ProSeoGame) {
  return {
    black: localizePlayer(g.black_player ?? "Black", "ko"),
    white: localizePlayer(g.white_player ?? "White", "ko"),
  };
}

// 한국어 검색 매칭용 키워드(바둑 기보)를 제목에 포함한다.
export function proGameTitle(g: ProSeoGame): string {
  const { black, white } = names(g);
  const event = formatProEvent(g.event ?? null, g.round ?? null, "ko");
  const paren = event ? ` (${event}${g.game_date ? `, ${g.game_date}` : ""})` : "";
  return `${black} vs ${white} 바둑 기보${paren} — inkbaduk`;
}

export function proGameDescription(g: ProSeoGame): string {
  const { black, white } = names(g);
  const blackRank = localizeRank(g.black_rank ?? null, "ko");
  const whiteRank = localizeRank(g.white_rank ?? null, "ko");
  const meta = [
    formatProEvent(g.event ?? null, g.round ?? null, "ko"),
    g.game_date,
    g.result ? `결과 ${formatGameResult(g.result, "ko")}` : null,
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    `${black}${blackRank ? ` ${blackRank}` : ""} vs ${white}${whiteRank ? ` ${whiteRank}` : ""}` +
    ` 대국을 KataGo로 수순별 복기·관전.` +
    (meta ? ` ${meta}.` : "")
  );
}

// 상세 페이지 본문용 사실 요약 — 값이 없는 절은 통째로 생략하고 평가·해설은 담지 않는다.
export function proGameSummary(g: ProSeoGame, locale: Locale): string {
  const label = (name: string | null | undefined, rank: string | null | undefined, fallback: string) => {
    const r = localizeRank(rank ?? null, locale);
    return `${localizePlayer(name ?? fallback, locale)}${r ? ` ${r}` : ""}`;
  };
  const black = label(g.black_player, g.black_rank, "Black");
  const white = label(g.white_player, g.white_rank, "White");
  const event = formatProEvent(g.event ?? null, g.round ?? null, locale);
  const parts = [
    event
      ? translate(locale, "spectate.proSummary.introEvent", { event, black, white })
      : translate(locale, "spectate.proSummary.intro", { black, white }),
  ];
  if (g.game_date) parts.push(translate(locale, "spectate.proSummary.date", { date: g.game_date }));
  if (g.move_count) parts.push(translate(locale, "spectate.proSummary.moves", { n: g.move_count }));
  if (g.result) {
    const result = formatGameResult(g.result, locale);
    parts.push(translate(locale, "spectate.proSummary.result", { result }));
  }
  if (g.board_size && g.komi !== undefined) {
    // translate는 같은 자리표시자를 한 번만 치환하므로 영어는 "19×19"를 미리 조립해 넘긴다.
    const size = locale === "en" ? `${g.board_size}×${g.board_size}` : g.board_size;
    const rules = { size, komi: g.komi, n: g.handicap ?? 0 };
    parts.push(
      translate(
        locale,
        g.handicap ? "spectate.proSummary.rulesHandicap" : "spectate.proSummary.rulesEven",
        rules,
      ),
    );
  }
  return parts.join(" ");
}

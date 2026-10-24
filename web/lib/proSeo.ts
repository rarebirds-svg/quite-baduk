// 프로 기보 상세 페이지의 SEO 제목·설명을 한글 기사명·기전명으로 조립한다(서버 안전).
import { formatGameResult } from "@/lib/formatResult";
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

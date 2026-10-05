// 레전드 기사 페르소나의 대국 중 한마디 — 언제(트리거) 무엇을(라인) 보여줄지 정한다.
// 카피는 i18n `game.personaLines.<player>.<trigger>_<n>`에 있고, 여기서는 순수 로직만.
// 소음을 막기 위해 최소 간격을 두고, 같은 트리거를 연달아 반복하지 않는다.

export type PersonaTrigger = "opening" | "capture" | "ahead" | "behind" | "midgame";

export interface PersonaEvent {
  /** AI 착수 직후의 총 수 */
  moveCount: number;
  /** 이번 AI 착수로 따낸 돌 수 */
  capturedByAi: number;
  /** AI 관점 승률 [0,1]. 모르면 null */
  aiWinrate: number | null;
}

export interface PersonaCommentaryState {
  lastShownMove: number;
  lastTrigger: PersonaTrigger | null;
}

export const initialCommentaryState = (): PersonaCommentaryState => ({
  lastShownMove: Number.NEGATIVE_INFINITY,
  lastTrigger: null,
});

export const MIN_GAP_MOVES = 8;
export const MIDGAME_EVERY = 20;
export const AHEAD_WINRATE = 0.78;
export const BEHIND_WINRATE = 0.25;

/**
 * 이번 AI 착수에 코멘트를 붙일지, 붙인다면 어떤 트리거인지.
 * 우선순위: 첫 수 인사 > 따냄 > 우세/열세 > 주기적 한마디.
 * 상태는 갱신하지 않는다 — 호출자가 라인을 실제로 보여준 뒤 markShown을 부른다.
 */
export function decideTrigger(
  ev: PersonaEvent,
  state: PersonaCommentaryState,
): PersonaTrigger | null {
  if (ev.moveCount <= 2 && state.lastTrigger === null) return "opening";
  const gapOk = ev.moveCount - state.lastShownMove >= MIN_GAP_MOVES;
  if (!gapOk) return null;
  const notRepeat = (tr: PersonaTrigger) => state.lastTrigger !== tr;
  if (ev.capturedByAi >= 2) return "capture";
  if (ev.aiWinrate !== null && ev.aiWinrate >= AHEAD_WINRATE && notRepeat("ahead")) return "ahead";
  if (ev.aiWinrate !== null && ev.aiWinrate <= BEHIND_WINRATE && notRepeat("behind")) return "behind";
  if (ev.capturedByAi >= 1) return "capture";
  if (ev.moveCount % MIDGAME_EVERY === 0) return "midgame";
  return null;
}

export function markShown(
  state: PersonaCommentaryState,
  moveCount: number,
  trigger: PersonaTrigger,
): PersonaCommentaryState {
  return { lastShownMove: moveCount, lastTrigger: trigger };
}

/** i18n에 있는 라인 중 하나를 고른다. 없으면 null (미등록 기사·트리거 안전). */
export function pickPersonaLine(
  t: (key: string) => string,
  playerId: string,
  trigger: PersonaTrigger,
  rng: () => number = Math.random,
): string | null {
  const lines: string[] = [];
  for (let i = 1; i <= 4; i++) {
    const key = `game.personaLines.${playerId}.${trigger}_${i}`;
    const v = t(key);
    if (v && v !== key) lines.push(v);
  }
  if (lines.length === 0) return null;
  return lines[Math.min(lines.length - 1, Math.floor(rng() * lines.length))];
}

import { describe, it, expect } from "vitest";
import {
  decideTrigger,
  initialCommentaryState,
  markShown,
  pickPersonaLine,
  MIN_GAP_MOVES,
  MIDGAME_EVERY,
} from "@/lib/personaComment";
import { translate } from "@/lib/i18n/translate";
import { PLAYER_GROUPS } from "@/components/PlayerPicker";

const ev = (moveCount: number, capturedByAi = 0, aiWinrate: number | null = 0.5) => ({
  moveCount,
  capturedByAi,
  aiWinrate,
});

describe("decideTrigger", () => {
  it("greets on the AI's first move, then respects the minimum gap", () => {
    let s = initialCommentaryState();
    expect(decideTrigger(ev(2), s)).toBe("opening");
    s = markShown(s, 2, "opening");
    expect(decideTrigger(ev(2 + MIN_GAP_MOVES - 1, 3), s)).toBeNull();
    expect(decideTrigger(ev(2 + MIN_GAP_MOVES, 3), s)).toBe("capture");
  });

  it("prefers captures, then winrate swings, then the periodic line", () => {
    const s = markShown(initialCommentaryState(), 0, "opening");
    expect(decideTrigger(ev(30, 2, 0.9), s)).toBe("capture");
    expect(decideTrigger(ev(30, 0, 0.9), s)).toBe("ahead");
    expect(decideTrigger(ev(30, 0, 0.1), s)).toBe("behind");
    expect(decideTrigger(ev(MIDGAME_EVERY * 2, 0, 0.5), s)).toBe("midgame");
    expect(decideTrigger(ev(MIDGAME_EVERY * 2 + 1, 0, 0.5), s)).toBeNull();
  });

  it("does not repeat ahead/behind back to back", () => {
    const s = markShown(initialCommentaryState(), 10, "ahead");
    expect(decideTrigger(ev(40, 0, 0.95), s)).toBe("midgame");
    expect(decideTrigger(ev(41, 0, 0.95), s)).toBeNull();
  });
});

describe("pickPersonaLine", () => {
  const tko = (k: string) => translate("ko", k);
  const ten = (k: string) => translate("en", k);
  const players = PLAYER_GROUPS.flatMap((g) => g.players);

  it("every legend has at least one line per trigger in both locales", () => {
    expect(players).toHaveLength(19);
    for (const pid of players) {
      for (const tr of ["opening", "capture", "ahead", "behind", "midgame"] as const) {
        expect(pickPersonaLine(tko, pid, tr, () => 0), `${pid}/${tr}/ko`).toBeTruthy();
        expect(pickPersonaLine(ten, pid, tr, () => 0), `${pid}/${tr}/en`).toBeTruthy();
      }
    }
  });

  it("returns null for unknown players and picks by rng", () => {
    expect(pickPersonaLine(tko, "nobody", "opening")).toBeNull();
    const a = pickPersonaLine(tko, "lee_changho", "opening", () => 0);
    const b = pickPersonaLine(tko, "lee_changho", "opening", () => 0.99);
    expect(a).not.toBe(b);
  });
});

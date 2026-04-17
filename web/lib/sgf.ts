// Minimal SGF parser (one game, main line only). Returns { size, komi, handicap, moves[] }
export interface SgfMove { color: "B" | "W"; coord: string | null; }
export interface SgfGame { size: number; komi: number; handicap: number; result: string | null; moves: SgfMove[]; }

export function parseSgf(text: string): SgfGame {
  const size = parseInt(/SZ\[(\d+)\]/.exec(text)?.[1] || "19", 10);
  const komi = parseFloat(/KM\[([\d.]+)\]/.exec(text)?.[1] || "6.5");
  const handicap = parseInt(/HA\[(\d+)\]/.exec(text)?.[1] || "0", 10);
  const result = /RE\[([^\]]+)\]/.exec(text)?.[1] ?? null;
  const moveRegex = /;([BW])\[([a-z]{0,2})\]/g;
  const moves: SgfMove[] = [];
  let m: RegExpExecArray | null;
  while ((m = moveRegex.exec(text))) {
    const color = m[1] as "B" | "W";
    if (!m[2]) { moves.push({ color, coord: null }); continue; }
    const col = m[2].charCodeAt(0) - 97;
    const row = m[2].charCodeAt(1) - 97;
    const gtp = `${"ABCDEFGHJKLMNOPQRST"[col]}${size - row}`;
    moves.push({ color, coord: gtp });
  }
  return { size, komi, handicap, result, moves };
}

export function buildSgf(game: SgfGame): string {
  let body = `;GM[1]FF[4]SZ[${game.size}]KM[${game.komi}]`;
  if (game.handicap > 0) body += `HA[${game.handicap}]`;
  if (game.result) body += `RE[${game.result}]`;
  for (const mv of game.moves) {
    if (mv.coord === null) { body += `;${mv.color}[]`; continue; }
    const m = /^([A-HJ-T])(\d+)$/.exec(mv.coord)!;
    const col = "ABCDEFGHJKLMNOPQRST".indexOf(m[1]);
    const row = game.size - parseInt(m[2], 10);
    body += `;${mv.color}[${String.fromCharCode(97+col)}${String.fromCharCode(97+row)}]`;
  }
  return `(${body})`;
}

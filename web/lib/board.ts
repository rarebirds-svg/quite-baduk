export const COLS = "ABCDEFGHJKLMNOPQRST";
export const BOARD = 19;
export const STAR_POINTS = [3, 9, 15];

export function xyToGtp(x: number, y: number): string {
  return `${COLS[x]}${BOARD - y}`;
}

export function gtpToXy(coord: string): [number, number] | null {
  if (coord.toLowerCase() === "pass") return null;
  const m = /^([A-HJ-T])(\d+)$/i.exec(coord);
  if (!m) return null;
  const x = COLS.indexOf(m[1].toUpperCase());
  const y = BOARD - parseInt(m[2], 10);
  if (x < 0 || y < 0 || y >= BOARD) return null;
  return [x, y];
}

export function parseBoard(flat: string): string[] {
  return flat.split("");
}

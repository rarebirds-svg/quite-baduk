export const COLS = "ABCDEFGHJKLMNOPQRST";
export const SUPPORTED_SIZES = [9, 13, 19] as const;
export type BoardSize = typeof SUPPORTED_SIZES[number];

const STAR_POINTS_BY_SIZE: Record<number, number[]> = {
  9: [2, 4, 6],
  13: [3, 6, 9],
  19: [3, 9, 15],
};

export function starPoints(size: number): number[] {
  return STAR_POINTS_BY_SIZE[size] ?? [];
}

export function totalCells(size: number): number {
  return size * size;
}

export function xyToGtp(x: number, y: number, size: number): string {
  return `${COLS[x]}${size - y}`;
}

export function gtpToXy(coord: string, size: number): [number, number] | null {
  if (coord.toLowerCase() === "pass") return null;
  const m = /^([A-HJ-T])(\d+)$/i.exec(coord);
  if (!m) return null;
  const cols = COLS.slice(0, size);
  const x = cols.indexOf(m[1].toUpperCase());
  if (x < 0) return null;
  const row = parseInt(m[2], 10);
  if (row < 1 || row > size) return null;
  const y = size - row;
  return [x, y];
}

export function parseBoard(flat: string): string[] {
  return flat.split("");
}

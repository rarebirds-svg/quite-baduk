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

/**
 * Apply a move and resolve captures, returning the new flat-string board.
 *
 * Client-side mirror of the backend rules engine's capture logic — used for
 * optimistic rendering so captured stones vanish the instant the user
 * clicks, instead of waiting for the server's state payload to come back.
 * Correctness: assumes the server validates (suicide, ko). Here we only do
 * the common case — place the stone, then for each neighboring opposite
 * group with zero liberties, remove all its stones.
 */
export function applyMoveWithCaptures(
  board: string,
  size: number,
  x: number,
  y: number,
  color: "B" | "W",
): string {
  if (x < 0 || x >= size || y < 0 || y >= size) return board;
  const idx = (xx: number, yy: number) => yy * size + xx;
  const here = idx(x, y);
  if (board[here] !== ".") return board;

  const cells = board.split("");
  cells[here] = color;
  const opp: "B" | "W" = color === "B" ? "W" : "B";

  const inBounds = (xx: number, yy: number) =>
    xx >= 0 && xx < size && yy >= 0 && yy < size;

  // Flood-fill the group starting at (sx, sy); return its stone cells and
  // the set of empty neighbor cells (liberties).
  const flood = (sx: number, sy: number): {
    stones: number[];
    hasLiberty: boolean;
  } => {
    const color0 = cells[idx(sx, sy)];
    const seen = new Set<number>();
    const stack: [number, number][] = [[sx, sy]];
    let hasLiberty = false;
    while (stack.length) {
      const [cx, cy] = stack.pop()!;
      const k = idx(cx, cy);
      if (seen.has(k)) continue;
      seen.add(k);
      for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]] as const) {
        const nx = cx + dx, ny = cy + dy;
        if (!inBounds(nx, ny)) continue;
        const nk = idx(nx, ny);
        const nc = cells[nk];
        if (nc === ".") {
          hasLiberty = true;
        } else if (nc === color0 && !seen.has(nk)) {
          stack.push([nx, ny]);
        }
      }
    }
    return { stones: Array.from(seen), hasLiberty };
  };

  // Capture adjacent opposite groups with no liberties.
  for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]] as const) {
    const nx = x + dx, ny = y + dy;
    if (!inBounds(nx, ny)) continue;
    if (cells[idx(nx, ny)] !== opp) continue;
    const { stones, hasLiberty } = flood(nx, ny);
    if (!hasLiberty) {
      for (const k of stones) cells[k] = ".";
    }
  }

  return cells.join("");
}

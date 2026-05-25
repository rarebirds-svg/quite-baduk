// board 코드블록 → 정적 SVG 변환. server-side에서 마크다운 변환 시 호출.
export interface BoardSpec {
  size: number;
  position: string[]; // 행별 size 문자 (.B W만)
  caption?: string;
}

const VALID_CELL = /[.BW]/;

/**
 * 마크다운 ```board 코드블록 내용을 파싱.
 * 형식: `size: <n>` `position: |` 다음 들여쓴 행들, `caption: <text>`.
 * 잘못된 입력은 fallback (size 기본 19, 행 padding, 잘못 문자 → .).
 */
export function parseBoardCodeBlock(source: string): BoardSpec {
  const lines = source.split("\n");
  let size = 19;
  let positionRaw: string[] = [];
  let caption: string | undefined;
  let inPosition = false;

  for (const line of lines) {
    const sizeMatch = line.match(/^\s*size:\s*(\d+)\s*$/);
    if (sizeMatch) {
      size = parseInt(sizeMatch[1], 10);
      inPosition = false;
      continue;
    }
    if (/^\s*position:\s*\|\s*$/.test(line)) {
      inPosition = true;
      continue;
    }
    const captionMatch = line.match(/^\s*caption:\s*(.+?)\s*$/);
    if (captionMatch) {
      caption = captionMatch[1];
      inPosition = false;
      continue;
    }
    if (inPosition) {
      const trimmed = line.replace(/^\s+/, "");
      if (trimmed === "") continue;
      positionRaw.push(trimmed);
    }
  }

  if (size !== 9 && size !== 13 && size !== 19) size = 19;

  // 행 padding + 잘못 문자 정규화
  const position: string[] = [];
  for (let r = 0; r < size; r++) {
    const raw = positionRaw[r] ?? "";
    const cells: string[] = [];
    for (let c = 0; c < size; c++) {
      const ch = raw[c] ?? ".";
      cells.push(VALID_CELL.test(ch) ? ch : ".");
    }
    position.push(cells.join(""));
  }

  return { size, position, caption };
}

const VIEWBOX = 480;
const PAD = 30;
const INNER = VIEWBOX - PAD * 2; // 420

interface CellCoord { x: number; y: number; }

function cellCenter(size: number, col: number, row: number): CellCoord {
  const step = INNER / (size - 1);
  return { x: PAD + col * step, y: PAD + row * step };
}

const STAR_POINTS: Record<number, [number, number][]> = {
  9: [[2,2],[6,2],[4,4],[2,6],[6,6]],
  13: [[3,3],[9,3],[6,6],[3,9],[9,9]],
  19: [[3,3],[9,3],[15,3],[3,9],[9,9],[15,9],[3,15],[9,15],[15,15]],
};

function escapeXml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/**
 * BoardSpec → 정적 SVG markup. 토큰은 CSS 변수(rgb(var(--...)))로 light/dark 자동 대응.
 */
export function boardToSvg(spec: BoardSpec): string {
  const { size, position, caption } = spec;
  const label = caption ? escapeXml(caption) : `${size}×${size} 바둑판 다이어그램`;
  const step = INNER / (size - 1);
  const stoneR = step * 0.45;
  const starR = step * 0.10;
  const parts: string[] = [];

  parts.push(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${VIEWBOX} ${VIEWBOX}" role="img" aria-label="${label}">`,
  );

  // grid lines
  for (let i = 0; i < size; i++) {
    const v = PAD + i * step;
    parts.push(
      `<line x1="${PAD}" y1="${v}" x2="${PAD + INNER}" y2="${v}" stroke="rgb(var(--ink-mute))" stroke-width="1" />`,
    );
    parts.push(
      `<line x1="${v}" y1="${PAD}" x2="${v}" y2="${PAD + INNER}" stroke="rgb(var(--ink-mute))" stroke-width="1" />`,
    );
  }

  // star points
  const stars = STAR_POINTS[size] ?? [];
  for (const [c, r] of stars) {
    const { x, y } = cellCenter(size, c, r);
    parts.push(`<circle class="star" cx="${x}" cy="${y}" r="${starR}" fill="rgb(var(--ink-mute))" />`);
  }

  // stones
  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      const ch = position[r]?.[c];
      if (ch !== "B" && ch !== "W") continue;
      const { x, y } = cellCenter(size, c, r);
      if (ch === "B") {
        parts.push(
          `<circle class="stone-black" cx="${x}" cy="${y}" r="${stoneR}" fill="rgb(var(--stone-black))" />`,
        );
      } else {
        parts.push(
          `<circle class="stone-white" cx="${x}" cy="${y}" r="${stoneR}" fill="rgb(var(--stone-white))" stroke="rgb(var(--ink-mute))" stroke-width="1" />`,
        );
      }
    }
  }

  parts.push(`</svg>`);
  return parts.join("");
}

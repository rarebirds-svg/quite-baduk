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

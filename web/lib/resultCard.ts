// 대국 결과 카드 — 커뮤니티 공유용 PNG를 만들기 위한 독립 SVG 생성기.
// Board.tsx는 CSS 변수(rgb(var(--ink)))를 쓰므로 캔버스에 그리면 색이 사라진다.
// 여기서는 lib/tokens.ts의 실제 값을 박아 브라우저 밖에서도 같은 색으로 렌더한다.
import { tokens } from "@/lib/tokens";
import { starPoints } from "@/lib/board";

export interface ResultCardSpec {
  size: number;
  board: string; // row-major, '.', 'B', 'W'
  title: string; // "닉네임 vs 이창호"
  subtitle: string; // "19×19 · 5급 · 실리형"
  result: string; // "백 불계승"
  brand?: string; // 기본 "Inkbaduk"
  /** 마지막 수 좌표 — 표시하면 어디서 끝났는지 한눈에 보인다. */
  lastMove?: { x: number; y: number } | null;
}

export const CARD_W = 1200;
export const CARD_H = 630; // OG 이미지 비율 — 커뮤니티 미리보기에 그대로 쓰인다.
const BOARD_PX = 560;
const BOARD_X = 40;
const BOARD_Y = (CARD_H - BOARD_PX) / 2;

function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function buildResultCardSvg(spec: ResultCardSpec): string {
  const c = tokens.light;
  const { size, board } = spec;
  const cell = BOARD_PX / (size + 1);
  const origin = cell; // 1칸 여백
  const at = (i: number) => BOARD_X + origin + i * cell;
  const atY = (i: number) => BOARD_Y + origin + i * cell;
  const parts: string[] = [];
  parts.push(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${CARD_W}" height="${CARD_H}" viewBox="0 0 ${CARD_W} ${CARD_H}">`,
    `<rect width="${CARD_W}" height="${CARD_H}" fill="${c.paper}"/>`,
    `<rect x="${BOARD_X}" y="${BOARD_Y}" width="${BOARD_PX}" height="${BOARD_PX}" fill="${c["paper-deep"]}"/>`,
  );
  for (let i = 0; i < size; i++) {
    const w = i === 0 || i === size - 1 ? 2 : 1;
    parts.push(
      `<line x1="${at(0)}" y1="${atY(i)}" x2="${at(size - 1)}" y2="${atY(i)}" stroke="${c.ink}" stroke-width="${w}"/>`,
      `<line x1="${at(i)}" y1="${atY(0)}" x2="${at(i)}" y2="${atY(size - 1)}" stroke="${c.ink}" stroke-width="${w}"/>`,
    );
  }
  const stars = starPoints(size);
  for (const sx of stars) for (const sy of stars) {
    parts.push(`<circle cx="${at(sx)}" cy="${atY(sy)}" r="${cell * 0.09}" fill="${c.ink}"/>`);
  }
  for (let idx = 0; idx < board.length; idx++) {
    const ch = board[idx];
    if (ch !== "B" && ch !== "W") continue;
    const x = idx % size;
    const y = Math.floor(idx / size);
    const fill = ch === "B" ? c["stone-black"] : c["stone-white"];
    const stroke = ch === "W" ? ` stroke="${c["ink-mute"]}" stroke-width="1"` : "";
    parts.push(`<circle cx="${at(x)}" cy="${atY(y)}" r="${cell * 0.46}" fill="${fill}"${stroke}/>`);
  }
  if (spec.lastMove) {
    const { x, y } = spec.lastMove;
    const stone = board[y * size + x];
    const dot = stone === "B" ? c["stone-white"] : c["stone-black"];
    parts.push(`<circle cx="${at(x)}" cy="${atY(y)}" r="${cell * 0.16}" fill="${dot}"/>`);
  }

  // 텍스트 컬럼
  const tx = BOARD_X + BOARD_PX + 56;
  const serif = "Newsreader, Georgia, 'Times New Roman', serif";
  const sans = "Pretendard, -apple-system, 'Segoe UI', Roboto, sans-serif";
  const mono = "'IBM Plex Mono', Menlo, monospace";
  parts.push(
    `<text x="${tx}" y="120" font-family="${sans}" font-size="18" font-weight="600" letter-spacing="4" fill="${c.oxblood}">${esc((spec.brand ?? "INKBADUK").toUpperCase())}</text>`,
    `<text x="${tx}" y="200" font-family="${serif}" font-size="52" fill="${c.ink}">${esc(spec.title)}</text>`,
    `<text x="${tx}" y="248" font-family="${mono}" font-size="22" fill="${c["ink-mute"]}">${esc(spec.subtitle)}</text>`,
    `<line x1="${tx}" y1="300" x2="${CARD_W - 60}" y2="300" stroke="${c["ink-faint"]}" stroke-width="1"/>`,
    `<text x="${tx}" y="400" font-family="${serif}" font-size="72" font-style="italic" fill="${c.ink}">${esc(spec.result)}</text>`,
    `<text x="${tx}" y="${CARD_H - 60}" font-family="${mono}" font-size="18" fill="${c["ink-faint"]}">inkbaduk.com</text>`,
    `</svg>`,
  );
  return parts.join("");
}

/** SVG 문자열을 PNG Blob으로 래스터화한다. 브라우저 전용(Image + canvas). */
export async function svgToPngBlob(svg: string, width = CARD_W, height = CARD_H): Promise<Blob> {
  const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml;charset=utf-8" }));
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = () => reject(new Error("svg_load_failed"));
      el.src = url;
    });
    const canvas = document.createElement("canvas");
    // 2x로 찍어 모바일 커뮤니티 업로드 시 흐려지지 않게 한다.
    canvas.width = width * 2;
    canvas.height = height * 2;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("canvas_unavailable");
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    return await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("png_encode_failed"))), "image/png"),
    );
  } finally {
    URL.revokeObjectURL(url);
  }
}

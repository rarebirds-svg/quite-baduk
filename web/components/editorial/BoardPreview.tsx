"use client";
// 랜딩 히어로용 정적 9×9 대국 프리뷰 — 실제 Board를 재사용해 "무엇을 얻는지" 보여준다
import Board from "@/components/Board";
import { useT } from "@/lib/i18n";

const SIZE = 9;
// 균형 잡힌 중반 국면 한 장면. index = y*SIZE + x.
const STONES: [number, number, "B" | "W"][] = [
  [2, 2, "B"], [6, 6, "B"], [4, 2, "B"], [2, 5, "B"], [3, 4, "B"], [5, 5, "B"],
  [6, 2, "W"], [2, 6, "W"], [6, 4, "W"], [4, 6, "W"], [5, 3, "W"], [3, 5, "W"],
];

const BOARD = (() => {
  const cells = Array(SIZE * SIZE).fill(".");
  for (const [x, y, c] of STONES) cells[y * SIZE + x] = c;
  return cells.join("");
})();

export function BoardPreview() {
  const t = useT();
  return (
    <figure className="mx-auto mt-12 flex max-w-[300px] flex-col items-center gap-3 md:mt-16">
      <Board size={SIZE} board={BOARD} lastMove={{ x: 5, y: 5 }} disabled />
      <figcaption className="font-mono text-[11px] uppercase tracking-label text-ink-mute text-center">
        {t("home.previewCaption")}
      </figcaption>
    </figure>
  );
}

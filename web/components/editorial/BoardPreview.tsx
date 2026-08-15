"use client";
// 랜딩 히어로용 정적 9×9 대국 프리뷰 — 실제 Board를 재사용해 "무엇을 얻는지" 보여준다
import Board from "@/components/Board";
import { QUICK_START_INPUT_ID } from "@/components/QuickStartForm";
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

// 프리뷰를 누르면 랜딩의 시작 폼으로 내려가 닉네임 입력에 포커스를 준다.
function jumpToStart() {
  document.getElementById("start")?.scrollIntoView({ behavior: "smooth", block: "start" });
  // 세션이 있으면 입력창 자체가 없으므로 스크롤만 한다.
  document.getElementById(QUICK_START_INPUT_ID)?.focus({ preventScroll: true });
}

export function BoardPreview() {
  const t = useT();
  return (
    <figure className="mx-auto mt-12 flex max-w-[300px] flex-col items-center gap-3 md:mt-16">
      <button
        type="button"
        onClick={jumpToStart}
        aria-label={t("home.boardPreviewCta")}
        className="group relative block w-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 focus-visible:ring-offset-paper"
      >
        <Board size={SIZE} board={BOARD} lastMove={{ x: 5, y: 5 }} disabled />
        <span
          aria-hidden
          className="absolute inset-0 flex items-center justify-center bg-paper/80 opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100"
        >
          <span className="border border-ink bg-paper px-3 py-1.5 font-sans text-sm font-semibold text-ink">
            {t("home.boardPreviewCta")}
          </span>
        </span>
      </button>
      <figcaption className="font-mono text-[11px] uppercase tracking-label text-ink-mute text-center">
        {t("home.previewCaption")}
      </figcaption>
    </figure>
  );
}

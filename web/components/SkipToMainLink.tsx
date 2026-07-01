"use client";
// 키보드 사용자가 네비게이션을 건너뛰고 본문으로 바로 가는 skip 링크 (포커스 시에만 노출)
import { useT } from "@/lib/i18n";

export default function SkipToMainLink() {
  const t = useT();
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-sm focus:border focus:border-ink focus:bg-paper focus:px-4 focus:py-2 focus:font-sans focus:text-sm focus:font-semibold focus:text-ink"
    >
      {t("a11y.skipToMain")}
    </a>
  );
}

"use client";
// 프로 기보 인덱스 상단 — i18n 훅이 필요한 히어로와 전체 목록 링크만 클라이언트로 남긴 조각.
import Link from "next/link";

import { Hero } from "@/components/editorial/Hero";
import { useT } from "@/lib/i18n";

export function ProIndexHeader() {
  const t = useT();
  return (
    <>
      <Hero title={t("spectate.tabPro")} subtitle={t("spectate.subtitle")} />
      {/* 검색 로봇이 전체 기보에 도달하도록 SSR 크롤 허브로 가는 정적 링크. */}
      <Link
        href="/spectate/pro/archive"
        className="inline-block font-mono text-xs uppercase tracking-label text-ink-faint transition-base hover:text-oxblood"
      >
        {t("spectate.archiveLink")}
      </Link>
    </>
  );
}

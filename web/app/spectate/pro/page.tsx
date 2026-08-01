"use client";
// 프로 기보 공개 인덱스 — 비로그인도 명국을 검색·열람하는 관전 진입점.
import Link from "next/link";

import { Hero } from "@/components/editorial/Hero";
import { ProGameList } from "@/components/ProGameList";
import { useT } from "@/lib/i18n";

export default function ProGameIndexPage() {
  const t = useT();
  return (
    <div className="space-y-4">
      <Hero title={t("spectate.tabPro")} subtitle={t("spectate.subtitle")} />
      {/* 검색 로봇이 전체 기보에 도달하도록 SSR 크롤 허브로 가는 정적 링크 — 목록은 클라이언트 fetch라 크롤 불가. */}
      <Link
        href="/spectate/pro/archive"
        className="inline-block font-mono text-xs uppercase tracking-label text-ink-faint transition-base hover:text-oxblood"
      >
        {t("spectate.archiveLink")}
      </Link>
      <ProGameList />
    </div>
  );
}

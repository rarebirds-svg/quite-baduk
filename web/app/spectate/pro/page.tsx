"use client";
// 프로 기보 공개 인덱스 — 비로그인도 명국을 검색·열람하는 관전 진입점.
import { Hero } from "@/components/editorial/Hero";
import { ProGameList } from "@/components/ProGameList";
import { useT } from "@/lib/i18n";

export default function ProGameIndexPage() {
  const t = useT();
  return (
    <div className="space-y-4">
      <Hero title={t("spectate.tabPro")} subtitle={t("spectate.subtitle")} />
      <ProGameList />
    </div>
  );
}

"use client";
// 쿼리 진입점 — /game/play?id= 형태. 앱 셸(정적 export)에서 사용한다.
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import GamePlayScreen from "@/components/screens/GamePlayScreen";

function PlayFromQuery() {
  const id = Number(useSearchParams().get("id"));
  if (!Number.isInteger(id) || id <= 0) return null;
  return <GamePlayScreen gameId={id} />;
}

export default function GamePlayPage() {
  return (
    <Suspense fallback={null}>
      <PlayFromQuery />
    </Suspense>
  );
}

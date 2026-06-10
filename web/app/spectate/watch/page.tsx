"use client";
// 쿼리 진입점 — /spectate/watch?id= 형태. 앱 셸(정적 export)에서 사용한다.
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import SpectateWatchScreen from "@/components/screens/SpectateWatchScreen";

function WatchFromQuery() {
  const id = Number(useSearchParams().get("id"));
  if (!Number.isInteger(id) || id <= 0) return null;
  return <SpectateWatchScreen gameId={id} />;
}

export default function SpectateWatchPage() {
  return (
    <Suspense fallback={null}>
      <WatchFromQuery />
    </Suspense>
  );
}

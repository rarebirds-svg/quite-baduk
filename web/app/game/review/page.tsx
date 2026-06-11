"use client";
// 쿼리 진입점 — /game/review?id= 형태. 앱 셸(정적 export)에서 사용한다.
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import GameReviewScreen from "@/components/screens/GameReviewScreen";

function ReviewFromQuery() {
  const id = Number(useSearchParams().get("id"));
  if (!Number.isInteger(id) || id <= 0) return null;
  return <GameReviewScreen gameId={id} />;
}

export default function GameReviewPage() {
  return (
    <Suspense fallback={null}>
      <ReviewFromQuery />
    </Suspense>
  );
}

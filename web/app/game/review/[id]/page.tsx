"use client";
// 웹 전용 path 진입점 — /game/review/[id] 기존 링크 호환. 본체는 GameReviewScreen.
import GameReviewScreen from "@/components/screens/GameReviewScreen";

export default function GameReviewByPath({ params }: { params: { id: string } }) {
  return <GameReviewScreen gameId={Number(params.id)} />;
}

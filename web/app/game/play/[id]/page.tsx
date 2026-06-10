"use client";
// 웹 전용 path 진입점 — /game/play/[id] 기존 링크 호환. 본체는 GamePlayScreen.
import GamePlayScreen from "@/components/screens/GamePlayScreen";

export default function GamePlayByPath({ params }: { params: { id: string } }) {
  return <GamePlayScreen gameId={Number(params.id)} />;
}

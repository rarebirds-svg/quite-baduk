"use client";
// 웹 전용 path 진입점 — /spectate/[id] 기존 링크 호환. 본체는 SpectateWatchScreen.
import SpectateWatchScreen from "@/components/screens/SpectateWatchScreen";

export default function SpectateWatchByPath({ params }: { params: { id: string } }) {
  return <SpectateWatchScreen gameId={Number(params.id)} />;
}

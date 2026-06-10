"use client";
// 웹 전용 path 진입점 — /spectate/pro/[id] 기존 링크 호환. 본체는 ProGameScreen.
import ProGameScreen from "@/components/screens/ProGameScreen";

export default function ProGameByPath({ params }: { params: { id: string } }) {
  return <ProGameScreen gameId={Number(params.id)} />;
}

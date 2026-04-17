"use client";

export default function ScorePanel({ captures }: { captures: Record<string, number> }) {
  return (
    <div className="flex gap-4 text-sm">
      <div>● 흑 잡은 수: {captures.B ?? 0}</div>
      <div>○ 백 잡은 수: {captures.W ?? 0}</div>
    </div>
  );
}

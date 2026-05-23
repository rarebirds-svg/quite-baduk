// 이 달의 명국 — 결정적 픽 단일 게임 랜딩 페이지.
import { notFound } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface MonthlyPick {
  yyyymm: string;
  id: number;
  black_player: string;
  white_player: string;
  event: string | null;
  game_date: string | null;
  result: string | null;
}

async function fetchPick(yyyymm: string): Promise<MonthlyPick | null> {
  try {
    const res = await fetch(`${API}/api/spectate/pro/pick/monthly/${yyyymm}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return (await res.json()) as MonthlyPick;
  } catch {
    return null;
  }
}

function adjacentMonth(yyyymm: string, delta: number): string {
  const [y, m] = yyyymm.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1 + delta, 1));
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

export default async function MonthlyPickPage({
  params,
}: {
  params: { yyyymm: string };
}) {
  const data = await fetchPick(params.yyyymm);
  if (data === null) notFound();
  const [y, m] = data.yyyymm.split("-");
  const prev = adjacentMonth(data.yyyymm, -1);
  const next = adjacentMonth(data.yyyymm, +1);
  return (
    <article className="prose">
      <header>
        <p className="text-ink-mute">{y}년 {Number(m)}월 이 달의 명국</p>
        <h1>
          {data.black_player} vs {data.white_player}
        </h1>
        {data.event && <p className="text-ink-mute">{data.event}</p>}
        {data.game_date && <p className="text-ink-faint">{data.game_date}</p>}
        {data.result && <p className="text-ink-faint">결과 {data.result}</p>}
      </header>
      <p className="not-prose">
        <a href={`/spectate/pro/${data.id}`}>관전·복기 →</a>
      </p>
      <nav className="not-prose flex gap-4 text-ink-mute text-sm">
        <a href={`/spectate/picks/monthly/${prev}`}>← {prev}</a>
        <a href={`/spectate/picks/monthly/${next}`}>{next} →</a>
        <a href={`/spectate/picks`}>전체 픽</a>
      </nav>
    </article>
  );
}

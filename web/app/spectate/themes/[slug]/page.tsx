// 테마 페이지 — backend API 결과를 서버 컴포넌트로 렌더.
import { notFound } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ThemeGame {
  id: number;
  black_player: string;
  white_player: string;
  event: string | null;
  game_date: string | null;
  result: string | null;
}

interface ThemeDetail {
  slug: string;
  label: string;
  description: string;
  total: number;
  games: ThemeGame[];
}

async function fetchTheme(slug: string): Promise<ThemeDetail | null> {
  try {
    const res = await fetch(`${API}/api/spectate/pro/theme/${slug}`, {
      next: { revalidate: 3600 },
    });
    if (res.status === 404) return null;
    if (!res.ok) return null;
    return (await res.json()) as ThemeDetail;
  } catch {
    return null;
  }
}

export default async function ThemePage({
  params,
}: {
  params: { slug: string };
}) {
  const data = await fetchTheme(params.slug);
  if (data === null) notFound();
  return (
    <article className="prose">
      <header>
        <h1>{data.label}</h1>
        <p className="text-ink-mute">{data.description}</p>
        <p className="text-ink-faint">총 {data.total}국</p>
      </header>
      <ul className="not-prose grid gap-2">
        {data.games.map((g) => (
          <li key={g.id}>
            <a href={`/spectate/pro/${g.id}`} className="block py-2 border-b border-ink-faint/20">
              <span className="font-medium">
                {g.black_player} vs {g.white_player}
              </span>
              {g.event && <span className="text-ink-mute"> · {g.event}</span>}
              {g.game_date && <span className="text-ink-faint"> · {g.game_date}</span>}
              {g.result && <span className="text-ink-faint"> · {g.result}</span>}
            </a>
          </li>
        ))}
      </ul>
    </article>
  );
}

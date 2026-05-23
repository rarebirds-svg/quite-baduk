// 프로 기보 상세 페이지용 레이아웃 — generateMetadata로 페이지별 title·description·canonical을 제공한다.
import type { Metadata } from "next";

const BASE = "https://inkbaduk.com";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ProGameMeta {
  id: number;
  black_player?: string | null;
  white_player?: string | null;
  event?: string | null;
  game_date?: string | null;
  result?: string | null;
}

export async function generateMetadata(
  { params }: { params: { id: string } },
): Promise<Metadata> {
  try {
    const res = await fetch(`${API}/api/spectate/pro/${params.id}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) {
      return { robots: { index: false, follow: false } };
    }
    const g = (await res.json()) as ProGameMeta;
    const black = g.black_player ?? "Black";
    const white = g.white_player ?? "White";
    const event = g.event
      ? ` (${g.event}${g.game_date ? `, ${g.game_date}` : ""})`
      : "";
    const title = `${black} vs ${white}${event} — inkbaduk`;
    const description =
      [g.event, g.game_date, g.result ? `결과 ${g.result}` : null]
        .filter(Boolean)
        .join(" · ") || "inkbaduk 프로 기보 관전";
    const canonical = `${BASE}/spectate/pro/${g.id}`;
    return {
      title,
      description,
      alternates: { canonical },
      openGraph: { title, description, url: canonical },
    };
  } catch {
    return {};
  }
}

export default function ProGameLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

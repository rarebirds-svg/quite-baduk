// 월간 픽 페이지 SEO 메타.
import type { Metadata } from "next";
import type { ReactNode } from "react";

const BASE = "https://inkbaduk.com";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface PickMeta {
  yyyymm: string;
  id: number;
  black_player: string;
  white_player: string;
  event: string | null;
  game_date: string | null;
  result: string | null;
}

export async function generateMetadata(
  { params }: { params: { yyyymm: string } },
): Promise<Metadata> {
  try {
    const res = await fetch(`${API}/api/spectate/pro/pick/monthly/${params.yyyymm}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return { robots: { index: false, follow: false } };
    const p = (await res.json()) as PickMeta;
    const [y, m] = p.yyyymm.split("-");
    const title = `${y}년 ${Number(m)}월 이 달의 명국 — ${p.black_player} vs ${p.white_player} — inkbaduk`;
    const description = [p.event, p.game_date, p.result ? `결과 ${p.result}` : null]
      .filter(Boolean)
      .join(" · ") || "inkbaduk 이 달의 명국";
    const canonical = `${BASE}/spectate/picks/monthly/${p.yyyymm}`;
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

export default function MonthlyPickLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

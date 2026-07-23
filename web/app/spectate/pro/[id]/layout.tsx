// 프로 기보 상세 페이지용 레이아웃 — generateMetadata로 페이지별 title·description·canonical을 제공한다.
import type { Metadata } from "next";

const BASE = "https://inkbaduk.com";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ProGameMeta {
  id: number;
  black_player?: string | null;
  white_player?: string | null;
  black_rank?: string | null;
  white_rank?: string | null;
  event?: string | null;
  round?: string | null;
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
    const eventParen = g.event
      ? ` (${g.event}${g.game_date ? `, ${g.game_date}` : ""})`
      : "";
    // 한국어 검색 매칭용 키워드(바둑 기보)를 제목에 포함. absolute로 브랜드 재부착 방지.
    const title = `${black} vs ${white} 바둑 기보${eventParen} — inkbaduk`;
    const blackName = `${black}${g.black_rank ? ` ${g.black_rank}` : ""}`;
    const whiteName = `${white}${g.white_rank ? ` ${g.white_rank}` : ""}`;
    const meta = [g.event, g.round, g.game_date, g.result ? `결과 ${g.result}` : null]
      .filter(Boolean)
      .join(" · ");
    const description =
      `${blackName} vs ${whiteName} 대국을 KataGo로 수순별 복기·관전.` +
      (meta ? ` ${meta}.` : "");
    const canonical = `${BASE}/spectate/pro/${g.id}`;
    return {
      title: { absolute: title },
      description,
      alternates: { canonical },
      openGraph: { title, description, url: canonical, type: "article", locale: "ko_KR" },
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

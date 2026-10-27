// 프로 기보 상세 페이지용 레이아웃 — generateMetadata로 페이지별 title·description·canonical을 제공한다.
import type { Metadata } from "next";
import { proGameDescription, proGameTitle, type ProSeoGame } from "@/lib/proSeo";

const BASE = "https://inkbaduk.com";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
    const g = (await res.json()) as ProSeoGame;
    // 한글 기사명·기전명으로 조립해 한국어 검색어와 맞춘다. absolute로 브랜드 재부착 방지.
    const title = proGameTitle(g);
    const description = proGameDescription(g);
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

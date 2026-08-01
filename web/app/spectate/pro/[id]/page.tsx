// 웹 전용 path 진입점 — 서버에서 기보를 fetch해 SSR(ISR 1h)로 렌더. 본체는 ProGameScreen.
import { notFound } from "next/navigation";
import ProGameScreen, {
  type ProGameDetail,
} from "@/components/screens/ProGameScreen";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const BASE = "https://inkbaduk.com";

// 탐색 경로 리치 표시를 위한 구조화 데이터 (schema.org BreadcrumbList).
function breadcrumbJsonLd(game: ProGameDetail) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "홈", item: `${BASE}/` },
      { "@type": "ListItem", position: 2, name: "프로 기보", item: `${BASE}/spectate/pro` },
      {
        "@type": "ListItem",
        position: 3,
        name: `${game.black_player} vs ${game.white_player}`,
        item: `${BASE}/spectate/pro/${game.id}`,
      },
    ],
  };
}

// 404(없는 기보)와 일시 장애(backend down 등)를 구분해 반환한다.
async function fetchProGame(
  id: string,
): Promise<ProGameDetail | "not_found" | "unavailable"> {
  if (!/^\d+$/.test(id)) return "not_found";
  try {
    const res = await fetch(`${API}/api/spectate/pro/${id}`, {
      next: { revalidate: 3600 },
    });
    if (res.status === 404) return "not_found";
    if (!res.ok) return "unavailable";
    return (await res.json()) as ProGameDetail;
  } catch {
    return "unavailable";
  }
}

export default async function ProGameByPath({
  params,
}: {
  params: { id: string };
}) {
  const game = await fetchProGame(params.id);
  if (game === "not_found") notFound();
  if (game === "unavailable") {
    // 서버 fetch 실패 시 기존 클라이언트 fetch로 폴백 — 동작은 전환 이전과 동일
    return <ProGameScreen gameId={Number(params.id)} />;
  }
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(breadcrumbJsonLd(game)).replace(/</g, "\\u003c"),
        }}
      />
      <ProGameScreen gameId={game.id} initialGame={game} />
    </>
  );
}

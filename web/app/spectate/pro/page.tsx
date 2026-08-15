// 프로 기보 공개 인덱스 — 첫 화면 목록을 서버에서 받아 SSR로 싣고, 검색·페이징은 클라이언트가 이어받는다.
import type { Metadata } from "next";

import {
  ProGameList,
  PRO_LIST_INITIAL_QUERY,
  type ProListResponse,
} from "@/components/ProGameList";

import { ProIndexHeader } from "./_ProIndexHeader";

const BASE = "https://inkbaduk.com";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const metadata: Metadata = {
  // 루트 layout의 template이 덧붙지 않도록 absolute로 고정한다.
  title: { absolute: "프로 기보 관전 — Inkbaduk" },
  description:
    "이창호·이세돌·신진서의 명국과 세계 기전 기보를 검색해 한 수씩 되짚어 봅니다. 비로그인으로 바로 관전할 수 있습니다.",
  alternates: { canonical: `${BASE}/spectate/pro` },
};

// ProGameList의 초기 상태(명국 · 최신순 · 첫 페이지)와 같은 질의를 미리 받아 둔다.
// 백엔드가 죽어 있으면 null을 돌려 종전처럼 클라이언트 fetch로 폴백한다.
// fetch의 revalidate가 이 페이지를 1시간 ISR로 만든다 — 앱 셸 정적 export를
// 깨뜨리는 세그먼트 단위 `export const revalidate`는 쓰지 않는다.
async function fetchInitialList(): Promise<ProListResponse | null> {
  try {
    const res = await fetch(`${API}/api/spectate/pro?${PRO_LIST_INITIAL_QUERY}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return (await res.json()) as ProListResponse;
  } catch {
    return null;
  }
}

export default async function ProGameIndexPage() {
  const initialData = await fetchInitialList();
  return (
    <div className="space-y-4">
      <ProIndexHeader />
      <ProGameList initialData={initialData} />
    </div>
  );
}

// 홈 라우트 — 서버에서 메타데이터와 속보 훅 데이터를 확정하고 본문은 클라이언트 랜딩 조각에 위임한다.
import type { Metadata } from "next";

import { getNewsHook } from "@/lib/newsHook";
import HomeLanding from "./_HomeLanding";

export const metadata: Metadata = {
  // 루트 layout의 template이 덧붙지 않도록 absolute로 고정 — 지금 노출 중인 제목 그대로다.
  title: { absolute: "Inkbaduk · 조용한 승부" },
  description:
    "닉네임 한 줄로 바로 시작하는 무료 AI 바둑. KataGo Human-SL이 9급부터 9단까지 사람처럼 두고, 대국이 끝나면 승부처를 복기합니다.",
  alternates: { canonical: "/" },
};

// 웹 배포는 매 요청 동적 렌더(news-hook.json 갱신이 재빌드 없이 즉시 반영되도록) —
// 앱 셸(BUILD_TARGET=app) 정적 export는 그대로 유지한다.
export const dynamic = process.env.BUILD_TARGET === "app" ? "force-static" : "force-dynamic";

export default function HomePage() {
  return <HomeLanding newsHook={getNewsHook()} />;
}

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

export default function HomePage() {
  return <HomeLanding newsHook={getNewsHook()} />;
}

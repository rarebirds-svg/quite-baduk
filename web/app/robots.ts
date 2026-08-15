// 검색 크롤러 규칙 — 공개 페이지만 허용하고 세션 게이트·관리자 경로는 차단
import type { MetadataRoute } from "next";

const BASE = "https://inkbaduk.com";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      // 공개 페이지만 색인. 아래 disallow 경로는 닉네임 세션이 필요해
      // 크롤러에겐 빈 화면이거나 홈으로 리다이렉트되므로 제외한다.
      // /daily(데일리 퍼즐)와 /spectate 허브는 익명 열람이 열려 색인 대상.
      // /spectate는 통짜로 막고 색인할 서브트리만 allow로 다시 여는 구조라,
      // 허브 자체는 종료 앵커(`/spectate$`)로 정확히 그 경로만 허용한다 —
      // 수명이 짧아 색인 가치가 없는 라이브 대국(/spectate/watch,
      // /spectate/<id>)은 더 짧은 매칭인 /spectate에 걸려 계속 차단된다.
      allow: [
        "/",
        "/daily",
        "/spectate$",
        "/spectate/pro",
        "/spectate/themes",
        "/spectate/picks",
      ],
      disallow: [
        "/admin",
        "/game",
        "/spectate",
        "/history",
        "/settings",
        "/dev",
        "/api",
      ],
    },
    sitemap: `${BASE}/sitemap.xml`,
  };
}

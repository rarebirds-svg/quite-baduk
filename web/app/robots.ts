// 검색 크롤러 규칙 — 공개 페이지만 허용하고 세션 게이트·관리자 경로는 차단
import type { MetadataRoute } from "next";

const BASE = "https://inkbaduk.com";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      // 공개 정적 페이지만 색인. 아래 경로는 닉네임 세션이 필요해
      // 크롤러에겐 빈 화면이거나 홈으로 리다이렉트되므로 제외한다.
      // /spectate는 통짜로 막되, 공개 콘텐츠 서브트리(pro·themes·picks)는
      // allow로 다시 열어 색인 개방한다 — 라이브 세션(/spectate/watch,
      // /spectate/<id>)은 더 짧은 매칭인 /spectate에 걸려 계속 차단된다.
      allow: ["/", "/spectate/pro", "/spectate/themes", "/spectate/picks"],
      disallow: [
        "/admin",
        "/game",
        "/daily",
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

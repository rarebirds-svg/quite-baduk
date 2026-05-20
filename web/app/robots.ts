// 검색 크롤러 규칙 — 공개 페이지만 허용하고 세션 게이트·관리자 경로는 차단
import type { MetadataRoute } from "next";

const BASE = "https://inkbaduk.com";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      // 공개 정적 페이지만 색인. 아래 경로는 닉네임 세션이 필요해
      // 크롤러에겐 빈 화면이거나 홈으로 리다이렉트되므로 제외한다.
      allow: "/",
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

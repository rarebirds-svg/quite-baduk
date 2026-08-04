/** @type {import('next').NextConfig} */
// BUILD_TARGET=app → Capacitor 정적 export. 그 외(웹)는 기본 빌드 + rewrite.
const isAppShell = process.env.BUILD_TARGET === "app";

const nextConfig = isAppShell
  ? { output: "export" }
  : {
      // `output`을 지정하지 않는다 — prod launchd(com.baduk.web)는 `npm start`(= next start)로
      // 구동하는데 Next.js는 standalone 산출물과 next start 조합을 지원하지 않는다(매 기동 경고).
      // 쓰이지 않는 .next/standalone 번들 생성도 함께 사라진다.
      async rewrites() {
        return [
          { source: "/api/:path*", destination: (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") + "/api/:path*" }
        ];
      },
      async redirects() {
        return [
          // 사활 페이지 슬러그 통합 — 옛 kasaeng을 정확한 슬러그 sahwal로 301 이전(중복 색인 제거).
          { source: "/glossary/kasaeng", destination: "/glossary/sahwal", permanent: true }
        ];
      }
    };
module.exports = nextConfig;

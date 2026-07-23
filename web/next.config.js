/** @type {import('next').NextConfig} */
// BUILD_TARGET=app → Capacitor 정적 export. 그 외(웹)는 기존 standalone + rewrite 불변.
const isAppShell = process.env.BUILD_TARGET === "app";

const nextConfig = isAppShell
  ? { output: "export" }
  : {
      output: "standalone",
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

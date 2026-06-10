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
      }
    };
module.exports = nextConfig;

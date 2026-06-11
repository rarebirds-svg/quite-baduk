import type { Metadata, Viewport } from "next";
import "./globals.css";
import TopNav from "@/components/TopNav";
import Footer from "@/components/Footer";
import AuthGate from "@/components/AuthGate";
import OfflineBanner from "@/components/OfflineBanner";
import { ThemeProviderClient } from "@/components/ThemeProviderClient";
import { fontVariables } from "@/lib/fonts";
import { Toaster } from "sonner";
import AppShellBridge from "@/components/AppShellBridge";

// --paper light: rgb(245 239 230) = #F5EFE6  (from globals.css :root)
// --paper dark:  rgb(28 25 23)   = #1C1917   (from globals.css .dark)

// 검색엔진 소유 확인 토큰 — 운영자가 각 웹마스터 도구 발급값으로 교체.
// 빈 값이면 해당 verification 메타태그는 출력되지 않는다.
// Google: DNS TXT 방식이라 코드 불필요(빈 값 유지).
// Naver: searchadvisor.naver.com HTML 태그.
// Baidu: ziyuan.baidu.com HTML 태그 — 단 계정 생성에 중국 본토 휴대폰
//        번호가 필요해 사실상 보류 상태. 토큰을 얻으면 여기에 넣는다.
const GOOGLE_SITE_VERIFICATION = "";
const NAVER_SITE_VERIFICATION = "2d39122f22d380e4b46daa65a00d0c7b0f4ff786";
const BAIDU_SITE_VERIFICATION = "";

const OTHER_VERIFICATION: Record<string, string> = {};
if (NAVER_SITE_VERIFICATION)
  OTHER_VERIFICATION["naver-site-verification"] = NAVER_SITE_VERIFICATION;
if (BAIDU_SITE_VERIFICATION)
  OTHER_VERIFICATION["baidu-site-verification"] = BAIDU_SITE_VERIFICATION;

export const metadata: Metadata = {
  metadataBase: new URL("https://inkbaduk.com"),
  title: { default: "Inkbaduk · 조용한 승부", template: "%s — Inkbaduk" },
  description:
    "KataGo Human-SL 인공지능과 두는 한국식 바둑. 9급부터 9단까지, 18인의 기풍을 골라 대국하고 복기에서 승부처를 분석합니다.",
  keywords: [
    "바둑",
    "온라인 바둑",
    "AI 바둑",
    "KataGo",
    "Human-SL",
    "바둑 복기",
    "바둑 AI 대국",
    "Inkbaduk",
    "잉크바둑",
    "baduk",
    "go game",
  ],
  applicationName: "Inkbaduk",
  alternates: { canonical: "/" },
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Inkbaduk",
  },
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/icons/icon.svg", type: "image/svg+xml" },
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  openGraph: {
    title: "Inkbaduk · 조용한 승부",
    description: "KataGo Human-SL과 두는 한국식 바둑 (9×9 · 13×13 · 19×19)",
    siteName: "Inkbaduk",
    url: "https://inkbaduk.com",
    locale: "ko_KR",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "Inkbaduk" }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Inkbaduk · 조용한 승부",
    description: "KataGo Human-SL과 두는 한국식 바둑",
    images: ["/og-image.png"],
  },
  verification: {
    ...(GOOGLE_SITE_VERIFICATION
      ? { google: GOOGLE_SITE_VERIFICATION }
      : {}),
    ...(Object.keys(OTHER_VERIFICATION).length
      ? { other: OTHER_VERIFICATION }
      : {}),
  },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F5EFE6" },
    { media: "(prefers-color-scheme: dark)", color: "#1C1917" },
  ],
};

// 검색 결과 리치 표시를 위한 구조화 데이터 (schema.org).
const JSON_LD = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": "https://inkbaduk.com/#website",
      url: "https://inkbaduk.com",
      name: "Inkbaduk",
      alternateName: "잉크바둑",
      description:
        "KataGo Human-SL 인공지능과 두는 한국식 바둑 — 9급부터 9단까지, 기풍 선택과 복기 승부처 분석.",
      inLanguage: "ko-KR",
    },
    {
      "@type": "Organization",
      "@id": "https://inkbaduk.com/#org",
      name: "Inkbaduk",
      url: "https://inkbaduk.com",
      logo: "https://inkbaduk.com/icons/icon-512.png",
    },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" className={fontVariables} suppressHydrationWarning>
      <head>
        <link
          rel="stylesheet"
          crossOrigin="anonymous"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }}
        />
      </head>
      <body className="bg-paper text-ink">
        <ThemeProviderClient>
          <AppShellBridge />
          <OfflineBanner />
          <AuthGate>
            <div className="flex min-h-dvh flex-col">
              <TopNav />
              <main className="p-4 max-w-7xl mx-auto w-full flex-1">
                {children}
              </main>
              <Footer />
            </div>
          </AuthGate>
          <Toaster position="top-center" richColors={false} closeButton />
        </ThemeProviderClient>
      </body>
    </html>
  );
}

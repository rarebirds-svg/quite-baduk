import type { Metadata, Viewport } from "next";
import "./globals.css";
import TopNav from "@/components/TopNav";
import AuthGate from "@/components/AuthGate";
import SessionBeacon from "@/components/SessionBeacon";
import { ThemeProviderClient } from "@/components/ThemeProviderClient";
import { fontVariables } from "@/lib/fonts";
import { Toaster } from "sonner";

// --paper light: rgb(245 239 230) = #F5EFE6  (from globals.css :root)
// --paper dark:  rgb(28 25 23)   = #1C1917   (from globals.css .dark)

export const metadata: Metadata = {
  title: { default: "Baduk — 조용한 승부", template: "%s — Baduk" },
  description: "KataGo Human-SL과 두는 한국식 바둑 (9×9 · 13×13 · 19×19)",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Baduk",
  },
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
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
      </head>
      <body className="bg-paper text-ink">
        <ThemeProviderClient>
          <SessionBeacon />
          <AuthGate>
            <TopNav />
            <main className="p-4 max-w-7xl mx-auto">{children}</main>
          </AuthGate>
          <Toaster position="top-center" richColors={false} closeButton />
        </ThemeProviderClient>
      </body>
    </html>
  );
}

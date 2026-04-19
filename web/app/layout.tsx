import type { Metadata } from "next";
import "./globals.css";
import TopNav from "@/components/TopNav";
import { ThemeProviderClient } from "@/components/ThemeProviderClient";
import { fontVariables } from "@/lib/fonts";
import { Toaster } from "sonner";

export const metadata: Metadata = {
  title: "Baduk — 조용한 승부",
  description: "KataGo Human-SL과 두는 한국식 바둑 (9×9 · 13×13 · 19×19)",
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
          <TopNav />
          <main className="p-4 max-w-7xl mx-auto">{children}</main>
          <Toaster position="top-center" richColors={false} closeButton />
        </ThemeProviderClient>
      </body>
    </html>
  );
}

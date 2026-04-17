import type { Metadata } from "next";
import "./globals.css";
import TopNav from "@/components/TopNav";
import { ThemeBootstrapper } from "@/components/ThemeBootstrapper";

export const metadata: Metadata = {
  title: "AI 바둑",
  description: "Play Go against KataGo AI (18k – 7d)"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <ThemeBootstrapper />
        <TopNav />
        <main className="p-4 max-w-7xl mx-auto">{children}</main>
      </body>
    </html>
  );
}

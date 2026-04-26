import { Newsreader, IBM_Plex_Mono } from "next/font/google";

/**
 * Pretendard loads via CDN <link> in app/layout.tsx head — not through next/font —
 * because Pretendard is not on Google Fonts. Sans stack is defined in globals.css :root.
 */
export const fontSerif = Newsreader({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-serif",
  axes: ["opsz"],
});

export const fontMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
  variable: "--font-mono",
});

export const fontVariables = [fontSerif.variable, fontMono.variable].join(" ");

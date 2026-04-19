"use client";
import { ThemeProvider } from "next-themes";
import { useEffect, type ReactNode } from "react";
import { initLocale } from "@/lib/i18n";

export function ThemeProviderClient({ children }: { children: ReactNode }) {
  useEffect(() => {
    initLocale();
  }, []);
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      {children}
    </ThemeProvider>
  );
}

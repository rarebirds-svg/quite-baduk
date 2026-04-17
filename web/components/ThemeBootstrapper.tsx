"use client";
import { useEffect } from "react";
import { applyTheme } from "@/lib/theme";
import { initLocale } from "@/lib/i18n";

export function ThemeBootstrapper() {
  useEffect(() => {
    applyTheme();
    initLocale();
  }, []);
  return null;
}

"use client";
import { useEffect, useState } from "react";
import { useT, useLocale, setLocale, type Locale } from "@/lib/i18n";
import { getTheme, setTheme, type Theme } from "@/lib/theme";
import RankPicker, { type Rank } from "@/components/RankPicker";

export default function SettingsPage() {
  const t = useT();
  const [locale] = useLocale();
  const [theme, setThemeState] = useState<Theme>("light");
  const [rank, setRank] = useState<Rank>("5k");

  useEffect(() => {
    setThemeState(getTheme());
    const saved = (localStorage.getItem("preferred_rank") as Rank | null) || "5k";
    setRank(saved);
  }, []);

  return (
    <div className="mt-6 space-y-4 max-w-sm">
      <h1 className="text-2xl font-bold">{t("settings.heading")}</h1>
      <RankPicker value={rank} onChange={(r) => { setRank(r); localStorage.setItem("preferred_rank", r); }} />
      <label className="flex flex-col gap-1">
        <span className="text-sm">{t("settings.language")}</span>
        <select value={locale} onChange={(e) => setLocale(e.target.value as Locale)} className="border rounded px-2 py-1 dark:bg-gray-900">
          <option value="ko">한국어</option>
          <option value="en">English</option>
        </select>
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-sm">{t("settings.theme")}</span>
        <select value={theme} onChange={(e) => { const v = e.target.value as Theme; setTheme(v); setThemeState(v); }} className="border rounded px-2 py-1 dark:bg-gray-900">
          <option value="light">{t("settings.themeLight")}</option>
          <option value="dark">{t("settings.themeDark")}</option>
        </select>
      </label>
    </div>
  );
}

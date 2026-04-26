"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useT, useLocale, setLocale, type Locale } from "@/lib/i18n";
import { useTheme } from "next-themes";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import RankPicker, { RANKS, type Rank } from "@/components/RankPicker";
import BoardBgSwitcher from "@/components/BoardBgSwitcher";

export default function SettingsPage() {
  const t = useT();
  const [locale] = useLocale();
  const { theme, setTheme } = useTheme();
  const [rank, setRank] = useState<Rank>("5k");
  const router = useRouter();
  const setSession = useAuthStore((s) => s.setSession);

  useEffect(() => {
    // Older builds supported a wider kyu range (18k/15k/12k/10k) that no
    // longer validates server-side. Ignore anything not in the current list
    // so the backend doesn't reject the saved value with 422.
    const saved = localStorage.getItem("preferred_rank");
    const valid = (RANKS as readonly string[]).includes(saved ?? "")
      ? (saved as Rank)
      : "5k";
    if (saved !== valid) localStorage.setItem("preferred_rank", valid);
    setRank(valid);
  }, []);

  const endSession = async () => {
    try {
      await api("/api/session/end", { method: "POST" });
    } catch {}
    setSession(null);
    router.push("/");
  };

  return (
    <div className="mt-6 space-y-4 max-w-sm">
      <h1 className="text-2xl font-bold">{t("settings.heading")}</h1>
      <label className="flex flex-col gap-1">
        <span className="text-sm">{t("settings.preferredRank")}</span>
        <RankPicker value={rank} onChange={(r) => { setRank(r); localStorage.setItem("preferred_rank", r); }} />
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-sm">{t("settings.language")}</span>
        <select value={locale} onChange={(e) => setLocale(e.target.value as Locale)} className="border rounded px-2 py-1 dark:bg-gray-900">
          <option value="ko">한국어</option>
          <option value="en">English</option>
        </select>
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-sm">{t("settings.theme")}</span>
        <select value={theme ?? "system"} onChange={(e) => setTheme(e.target.value)} className="border rounded px-2 py-1 dark:bg-gray-900">
          <option value="light">{t("settings.themeLight")}</option>
          <option value="dark">{t("settings.themeDark")}</option>
          <option value="system">System</option>
        </select>
      </label>
      <BoardBgSwitcher />
      <div className="pt-6 border-t border-ink-faint">
        <button
          onClick={endSession}
          className="border border-ink/10 rounded-sm px-4 py-2 text-sm hover:bg-paper-deep"
        >
          {t("session.endSession")}
        </button>
      </div>
    </div>
  );
}

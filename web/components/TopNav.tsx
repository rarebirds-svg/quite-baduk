"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useT, setLocale, useLocale } from "@/lib/i18n";
import { getTheme, setTheme, type Theme } from "@/lib/theme";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { useRouter } from "next/navigation";

export default function TopNav() {
  const t = useT();
  const [locale] = useLocale();
  const [theme, setThemeState] = useState<Theme>("light");
  const { user, setUser } = useAuthStore();
  const router = useRouter();

  useEffect(() => { setThemeState(getTheme()); }, []);
  useEffect(() => {
    (async () => {
      try {
        const me = await api<{ id: number; email: string; display_name: string; preferred_rank?: string | null; locale?: string; theme?: string }>("/api/auth/me");
        setUser(me);
      } catch { setUser(null); }
    })();
  }, [setUser]);

  const toggleTheme = () => {
    const nt: Theme = theme === "light" ? "dark" : "light";
    setTheme(nt);
    setThemeState(nt);
  };

  const logout = async () => {
    try { await api("/api/auth/logout", { method: "POST" }); } catch {}
    setUser(null);
    router.push("/");
  };

  return (
    <nav className="border-b dark:border-gray-800 px-4 py-3 flex items-center gap-4">
      <Link href="/" className="font-bold">{t("app.title")}</Link>
      <Link href="/game/new" className="text-sm">{t("nav.newGame")}</Link>
      <Link href="/history" className="text-sm">{t("nav.history")}</Link>
      <Link href="/settings" className="text-sm">{t("nav.settings")}</Link>
      <div className="ml-auto flex items-center gap-3">
        <button onClick={() => setLocale(locale === "ko" ? "en" : "ko")} aria-label="Toggle language" className="text-xs px-2 py-1 border rounded">
          {locale === "ko" ? "EN" : "한"}
        </button>
        <button onClick={toggleTheme} aria-label="Toggle theme" className="text-xs px-2 py-1 border rounded">
          {theme === "light" ? "🌙" : "☀"}
        </button>
        {user ? (
          <>
            <span className="text-xs">{user.display_name}</span>
            <button onClick={logout} className="text-xs underline">{t("nav.logout")}</button>
          </>
        ) : (
          <>
            <Link href="/login" className="text-xs">{t("nav.login")}</Link>
            <Link href="/signup" className="text-xs">{t("nav.signup")}</Link>
          </>
        )}
      </div>
    </nav>
  );
}

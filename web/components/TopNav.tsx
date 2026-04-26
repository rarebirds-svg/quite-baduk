"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { Sun, Moon, Laptop } from "lucide-react";
import { useT, useLocale, setLocale } from "@/lib/i18n";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { BrandMark } from "@/components/editorial/BrandMark";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

export default function TopNav() {
  const t = useT();
  const [locale] = useLocale();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { session, setSession, isAdmin, setIsAdmin } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  // Resolve admin status from the backend once per session. We intentionally
  // don't trust the nickname alone — the server decides and returns a flag.
  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await api<{ is_admin: boolean }>("/api/admin/me");
        if (!cancelled) setIsAdmin(Boolean(r.is_admin));
      } catch {
        if (!cancelled) setIsAdmin(false);
      }
    })();
    return () => { cancelled = true; };
  }, [session, setIsAdmin]);

  // Hide the nav entirely on the nickname gate — that screen is its own hero
  if (pathname === "/") return null;

  const endSession = async () => {
    try {
      await api("/api/session/end", { method: "POST" });
    } catch {}
    setSession(null);
    router.push("/");
  };

  const ThemeIcon = !mounted
    ? Laptop
    : theme === "system"
      ? Laptop
      : resolvedTheme === "dark"
        ? Moon
        : Sun;
  const nextTheme = theme === "light" ? "dark" : theme === "dark" ? "system" : "light";

  return (
    <nav className="border-b border-ink-faint bg-paper">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4">
        <Link href="/game/new" className="flex items-center gap-2" aria-label={t("app.title")}>
          <BrandMark size={20} />
          <span className="font-serif text-lg font-semibold tracking-tight">Baduk</span>
          <span aria-hidden className="h-3 w-px bg-ink-faint" />
          <span className="font-mono text-[10px] uppercase tracking-label text-ink-mute">
            {t("nav.volume")}
          </span>
        </Link>

        <div className="ml-auto flex items-center gap-2">
          {session && (
            <Button asChild size="sm" variant="outline">
              <Link href="/game/new">{t("nav.newGame")}</Link>
            </Button>
          )}

          <button
            onClick={() => setLocale(locale === "ko" ? "en" : "ko")}
            aria-label="Toggle language"
            className="flex h-9 w-9 items-center justify-center border border-ink-faint font-mono text-[10px] font-semibold uppercase tracking-label text-ink-mute hover:bg-paper-deep"
          >
            {locale === "ko" ? "EN" : "KO"}
          </button>

          <button
            onClick={() => setTheme(nextTheme)}
            aria-label={`Theme: ${theme}`}
            className="flex h-9 w-9 items-center justify-center border border-ink-faint text-ink-mute hover:bg-paper-deep hover:text-ink"
          >
            <ThemeIcon size={16} strokeWidth={1.5} />
          </button>

          {session && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-2">
                  <span aria-hidden className="h-2 w-2 rounded-full bg-ink" />
                  {session.nickname}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem asChild>
                  <Link href="/history">{t("nav.history")}</Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/settings">{t("nav.settings")}</Link>
                </DropdownMenuItem>
                {isAdmin && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                      <Link href="/admin" className="text-oxblood">
                        {t("nav.admin")}
                      </Link>
                    </DropdownMenuItem>
                  </>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={endSession}>{t("session.endSession")}</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>
    </nav>
  );
}

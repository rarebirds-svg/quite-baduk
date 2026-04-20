"use client";
import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
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
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/cn";

export default function TopNav() {
  const t = useT();
  const [locale] = useLocale();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const { user, setUser } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    (async () => {
      try {
        const me = await api<{
          id: number;
          email: string;
          display_name: string;
          preferred_rank?: string | null;
          locale?: string;
          theme?: string;
        }>("/api/auth/me");
        setUser(me);
      } catch {
        setUser(null);
      }
    })();
  }, [setUser]);

  const logout = async () => {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } catch {}
    setUser(null);
    router.push("/");
  };

  const ThemeIcon = theme === "system" ? Laptop : resolvedTheme === "dark" ? Moon : Sun;
  const nextTheme = theme === "light" ? "dark" : theme === "dark" ? "system" : "light";

  return (
    <nav className="border-b border-ink-faint bg-paper">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4">
        <Link href="/" className="flex items-center gap-2" aria-label={t("app.title")}>
          <BrandMark size={20} />
          <span className="font-serif text-lg font-semibold tracking-tight">Baduk</span>
          <span aria-hidden className="h-3 w-px bg-ink-faint" />
          <span className="font-mono text-[10px] uppercase tracking-label text-ink-mute">
            {t("nav.volume")}
          </span>
        </Link>

        <div className="ml-auto flex items-center gap-2">
          {user && (
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

          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-2">
                  <span aria-hidden className="h-2 w-2 rounded-full bg-ink" />
                  {user.display_name}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>{user.email}</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/history">{t("nav.history")}</Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/settings">{t("nav.settings")}</Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout}>{t("nav.logout")}</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <>
              <Button asChild size="sm" variant="ghost">
                <Link href="/login">{t("nav.login")}</Link>
              </Button>
              <Button asChild size="sm" variant="default">
                <Link href="/signup">{t("nav.signup")}</Link>
              </Button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

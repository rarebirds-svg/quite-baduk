"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useT } from "@/lib/i18n";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import { Hero } from "@/components/editorial/Hero";
import { EmptyState } from "@/components/editorial/EmptyState";
import { BrandMark } from "@/components/editorial/BrandMark";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type RecentGame = {
  id: number;
  board_size: number;
  ai_rank?: string;
  status: string;
  result: string | null;
  started_at: string;
  finished_at: string | null;
};

export default function Home() {
  const t = useT();
  const { user } = useAuthStore();
  const [recent, setRecent] = useState<RecentGame[] | null>(null);

  useEffect(() => {
    if (!user) return;
    (async () => {
      try {
        const res = await api<{ games?: RecentGame[] } | RecentGame[]>(
          "/api/games"
        );
        const games = Array.isArray(res) ? res : res.games ?? [];
        setRecent(games.slice(0, 3));
      } catch {
        setRecent([]);
      }
    })();
  }, [user]);

  return (
    <div className="flex flex-col gap-10 py-6">
      <Hero
        title={t("home.heading")}
        subtitle={t("home.sub")}
        volume={t("nav.volume")}
      />

      <div className="flex flex-wrap gap-3">
        <Button asChild size="lg">
          <Link href={user ? "/game/new" : "/signup"}>
            {user ? t("home.startButton") : t("home.guestSignup")}
          </Link>
        </Button>
        {user && (
          <Button asChild size="lg" variant="ghost">
            <Link href="/history">{t("home.ctaHistory")}</Link>
          </Button>
        )}
      </div>

      {user && (
        <section className="flex flex-col gap-4">
          <RuleDivider label={t("home.sectionRecent")} weight="strong" />
          {recent === null ? (
            <div className="h-24 border border-ink-faint bg-paper-deep" aria-busy />
          ) : recent.length === 0 ? (
            <EmptyState
              icon={<BrandMark size={32} className="opacity-40" />}
              title={t("home.sectionEmpty")}
              action={
                <Button asChild>
                  <Link href="/game/new">{t("home.startButton")}</Link>
                </Button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {recent.map((g) => (
                <Link key={g.id} href={`/game/review/${g.id}`}>
                  <Card className="transition-colors hover:bg-paper-deep/70">
                    <CardHeader>
                      <CardTitle>
                        {g.board_size} × {g.board_size}
                        {g.result ? ` · ${g.result}` : g.status === "active" ? " · 진행중" : ""}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="font-mono text-xs text-ink-mute">
                        {g.started_at.slice(0, 10)}
                        {g.ai_rank && ` · 상대 ${g.ai_rank}`}
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

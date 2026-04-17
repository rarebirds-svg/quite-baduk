"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface Stats { total: number; wins: number; losses: number; breakdown: unknown[] }
interface Game { id: number; ai_rank: string; handicap: number; status: string; result: string | null; started_at: string }

export default function HistoryPage() {
  const t = useT();
  const [stats, setStats] = useState<Stats | null>(null);
  const [games, setGames] = useState<Game[]>([]);

  useEffect(() => {
    api<Stats>("/api/stats").then(setStats).catch(() => {});
    api<Game[]>("/api/games").then(setGames).catch(() => {});
  }, []);

  return (
    <div className="mt-6 space-y-4">
      {stats && (
        <div className="text-sm">
          {t("history.total")}: {stats.total}, {t("history.wins")}: {stats.wins}, {t("history.losses")}: {stats.losses}
        </div>
      )}
      {games.length === 0 ? (
        <div className="text-sm text-gray-500">{t("history.empty")}</div>
      ) : (
        <table className="w-full text-sm">
          <thead><tr><th className="text-left">#</th><th className="text-left">Rank</th><th className="text-left">HA</th><th className="text-left">Result</th><th className="text-left">Started</th><th></th></tr></thead>
          <tbody>
            {games.map((g) => (
              <tr key={g.id} className="border-t dark:border-gray-800">
                <td className="py-1">{g.id}</td>
                <td>{g.ai_rank}</td>
                <td>{g.handicap}</td>
                <td>{g.result || g.status}</td>
                <td>{new Date(g.started_at).toLocaleString()}</td>
                <td className="flex gap-2 py-1">
                  <Link className="underline" href={`/game/review/${g.id}`}>review</Link>
                  <a className="underline" href={`/api/games/${g.id}/sgf`}>SGF</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

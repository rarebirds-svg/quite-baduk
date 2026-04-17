"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import RankPicker, { type Rank } from "@/components/RankPicker";
import HandicapPicker from "@/components/HandicapPicker";
import { api, ApiError } from "@/lib/api";
import { useT } from "@/lib/i18n";

export default function NewGamePage() {
  const t = useT();
  const router = useRouter();
  const [rank, setRank] = useState<Rank>("5k");
  const [handicap, setHandicap] = useState<number>(0);
  const [userColor, setUserColor] = useState<"black" | "white">("black");
  const [err, setErr] = useState<string | null>(null);

  async function create() {
    setErr(null);
    try {
      const body = JSON.stringify({ ai_rank: rank, handicap, user_color: handicap > 0 ? "black" : userColor });
      const game = await api<{ id: number }>("/api/games", { method: "POST", body });
      router.push(`/game/play/${game.id}`);
    } catch (e: unknown) {
      setErr(t(`errors.${(e as ApiError).code || "validation"}`));
    }
  }

  return (
    <div className="space-y-4 max-w-md mt-6">
      <h1 className="text-2xl font-bold">{t("nav.newGame")}</h1>
      <RankPicker value={rank} onChange={setRank} />
      <HandicapPicker value={handicap} onChange={setHandicap} />
      {handicap === 0 && (
        <label className="flex flex-col gap-1">
          <span className="text-sm">{t("game.color")}</span>
          <select value={userColor} onChange={(e) => setUserColor(e.target.value as "black" | "white")} className="border rounded px-2 py-1 dark:bg-gray-900">
            <option value="black">{t("game.colorBlack")}</option>
            <option value="white">{t("game.colorWhite")}</option>
          </select>
        </label>
      )}
      {err && <div className="text-red-600 text-sm">{err}</div>}
      <button onClick={create} className="px-4 py-2 bg-blue-600 text-white rounded">{t("game.create")}</button>
    </div>
  );
}

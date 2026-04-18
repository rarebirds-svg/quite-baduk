"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import RankPicker, { type Rank } from "@/components/RankPicker";
import HandicapPicker from "@/components/HandicapPicker";
import BoardSizePicker from "@/components/BoardSizePicker";
import { api, ApiError } from "@/lib/api";
import { useT } from "@/lib/i18n";
import type { BoardSize } from "@/lib/board";

const VALID_HANDICAPS_BY_SIZE: Record<number, number[]> = {
  9: [0, 2, 3, 4, 5],
  13: [0, 2, 3, 4, 5, 6, 7, 8, 9],
  19: [0, 2, 3, 4, 5, 6, 7, 8, 9],
};

export default function NewGamePage() {
  const t = useT();
  const router = useRouter();
  const [boardSize, setBoardSize] = useState<BoardSize>(19);
  const [rank, setRank] = useState<Rank>("5k");
  const [handicap, setHandicap] = useState<number>(0);
  const [userColor, setUserColor] = useState<"black" | "white">("black");
  const [err, setErr] = useState<string | null>(null);
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    api("/api/auth/me")
      .then(() => setAuthed(true))
      .catch(() => {
        setAuthed(false);
        router.replace("/login?next=/game/new");
      });
  }, [router]);

  function pickSize(s: BoardSize) {
    setBoardSize(s);
    if (!VALID_HANDICAPS_BY_SIZE[s].includes(handicap)) {
      setHandicap(0);
    }
  }

  async function create() {
    setErr(null);
    try {
      const body = JSON.stringify({
        ai_rank: rank,
        handicap,
        user_color: handicap > 0 ? "black" : userColor,
        board_size: boardSize,
      });
      const game = await api<{ id: number }>("/api/games", { method: "POST", body });
      router.push(`/game/play/${game.id}`);
    } catch (e: unknown) {
      const code = (e as ApiError).code || "validation";
      if ((e as ApiError).status === 401) {
        router.replace("/login?next=/game/new");
        return;
      }
      setErr(t(`errors.${code}`));
    }
  }

  if (authed === null) {
    return <div className="mt-6 text-sm text-gray-500">...</div>;
  }

  return (
    <div className="space-y-4 max-w-md mt-6">
      <h1 className="text-2xl font-bold">{t("nav.newGame")}</h1>
      <BoardSizePicker value={boardSize} onChange={pickSize} />
      <RankPicker value={rank} onChange={setRank} />
      <HandicapPicker boardSize={boardSize} value={handicap} onChange={setHandicap} />
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

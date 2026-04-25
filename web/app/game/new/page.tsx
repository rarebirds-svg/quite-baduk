"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useT } from "@/lib/i18n";
import { api, ApiError } from "@/lib/api";
import type { BoardSize } from "@/lib/board";
import { Hero } from "@/components/editorial/Hero";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Label } from "@/components/ui/label";
import RankPicker, { RANKS, type Rank } from "@/components/RankPicker";
import BoardSizePicker from "@/components/BoardSizePicker";
import HandicapPicker from "@/components/HandicapPicker";
import type { AiStyle } from "@/components/StylePicker";
import PlayerPicker, {
  type PlayerId,
  PLAYER_GROUPS,
} from "@/components/PlayerPicker";
import { toast } from "sonner";

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
  const [aiPlayer, setAiPlayer] = useState<PlayerId>("shin_jinseo");
  const [handicap, setHandicap] = useState(0);
  const [userColor, setUserColor] = useState<"black" | "white">("black");
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

  const aiStyle: AiStyle = (PLAYER_GROUPS.find((g) =>
    g.players.includes(aiPlayer),
  )?.style ?? "balanced") as AiStyle;

  useEffect(() => {
    (async () => {
      try {
        await api("/api/session");
        setAuthed(true);
      } catch {
        setAuthed(false);
        router.replace("/");
      }
    })();
  }, [router]);

  useEffect(() => {
    if (!VALID_HANDICAPS_BY_SIZE[boardSize].includes(handicap)) setHandicap(0);
  }, [boardSize, handicap]);

  const onCreate = async () => {
    setBusy(true);
    try {
      // Snapshot the user's self-declared rank from settings (falling back
      // to the same value they picked for the AI). Used only for history.
      // A legacy localStorage value (e.g. "10k" from an older build) would
      // fail backend validation — coerce to a value the current schema
      // accepts, defaulting to the AI rank the user just picked.
      let userRank: string = rank;
      try {
        const stored = localStorage.getItem("preferred_rank");
        if (stored && (RANKS as readonly string[]).includes(stored)) {
          userRank = stored;
        }
      } catch {
        userRank = rank;
      }
      const res = await api<{ id: number }>("/api/games", {
        method: "POST",
        body: JSON.stringify({
          ai_rank: rank,
          ai_style: aiStyle,
          ai_player: aiPlayer,
          handicap,
          user_color: handicap > 0 ? "black" : userColor,
          board_size: boardSize,
          user_rank: userRank,
        }),
      });
      router.push(`/game/play/${res.id}`);
    } catch (e: unknown) {
      const code = (e as ApiError).code || "validation";
      if ((e as ApiError).status === 401) {
        router.replace("/");
        return;
      }
      toast.error(t(`errors.${code}`));
    } finally {
      setBusy(false);
    }
  };

  if (authed === null) return null;

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-5 py-6">
      <Hero title={t("game.newGame")} subtitle={t("game.newGameSubtitle")} />

      <div className="divide-y divide-ink-faint/40 border-y border-ink-faint/40">
        <section className="flex items-center justify-between gap-4 py-3">
          <Label
            htmlFor="rank-picker"
            className="text-xs font-semibold uppercase tracking-label text-ink-mute"
          >
            {t("game.rank")}
          </Label>
          <div className="w-40">
            <RankPicker value={rank} onChange={setRank} />
          </div>
        </section>

        <section className="flex items-center justify-between gap-4 py-3">
          <Label className="text-xs font-semibold uppercase tracking-label text-ink-mute">
            {t("game.boardSize")}
          </Label>
          <BoardSizePicker value={boardSize} onChange={setBoardSize} />
        </section>

        <section className="flex items-center justify-between gap-4 py-3">
          <Label
            htmlFor="handicap-picker"
            className="text-xs font-semibold uppercase tracking-label text-ink-mute"
          >
            {t("game.handicap")}
          </Label>
          <div className="w-40">
            <HandicapPicker
              boardSize={boardSize}
              value={handicap}
              onChange={setHandicap}
            />
          </div>
        </section>

        {handicap === 0 && (
          <section className="flex items-center justify-between gap-4 py-3">
            <Label className="text-xs font-semibold uppercase tracking-label text-ink-mute">
              {t("game.color")}
            </Label>
            <ToggleGroup
              type="single"
              value={userColor}
              onValueChange={(v) => v && setUserColor(v as "black" | "white")}
            >
              <ToggleGroupItem value="black">
                {t("game.colorBlack")}
              </ToggleGroupItem>
              <ToggleGroupItem value="white">
                {t("game.colorWhite")}
              </ToggleGroupItem>
            </ToggleGroup>
          </section>
        )}
      </div>

      <section className="flex flex-col gap-3">
        <div className="flex items-baseline gap-2">
          <Label className="text-xs font-semibold uppercase tracking-label text-ink-mute">
            {t("game.aiPlayer")}
          </Label>
          <span className="font-sans text-xs text-ink-mute">
            {t("game.aiPlayerHint")}
          </span>
        </div>
        <PlayerPicker value={aiPlayer} onChange={setAiPlayer} />
      </section>

      <Button
        className="mt-2 w-full"
        size="lg"
        onClick={onCreate}
        disabled={busy}
      >
        {busy ? "…" : t("game.start")}
      </Button>
    </div>
  );
}

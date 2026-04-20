"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useT } from "@/lib/i18n";
import { api, ApiError } from "@/lib/api";
import type { BoardSize } from "@/lib/board";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { DataBlock } from "@/components/editorial/DataBlock";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Label } from "@/components/ui/label";
import RankPicker, { type Rank } from "@/components/RankPicker";
import BoardSizePicker from "@/components/BoardSizePicker";
import HandicapPicker from "@/components/HandicapPicker";
import { toast } from "sonner";

const VALID_HANDICAPS_BY_SIZE: Record<number, number[]> = {
  9: [0, 2, 3, 4, 5],
  13: [0, 2, 3, 4, 5, 6, 7, 8, 9],
  19: [0, 2, 3, 4, 5, 6, 7, 8, 9],
};

export default function NewGamePage() {
  const t = useT();
  const router = useRouter();
  const [boardSize, setBoardSize] = useState<BoardSize>(9);
  const [rank, setRank] = useState<Rank>("5k");
  const [handicap, setHandicap] = useState(0);
  const [userColor, setUserColor] = useState<"black" | "white">("black");
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        await api("/api/auth/me");
        setAuthed(true);
      } catch {
        setAuthed(false);
        router.replace("/login?next=/game/new");
      }
    })();
  }, [router]);

  useEffect(() => {
    if (!VALID_HANDICAPS_BY_SIZE[boardSize].includes(handicap)) setHandicap(0);
  }, [boardSize, handicap]);

  const onCreate = async () => {
    setBusy(true);
    try {
      const res = await api<{ id: number }>("/api/games", {
        method: "POST",
        body: JSON.stringify({
          ai_rank: rank,
          handicap,
          user_color: handicap > 0 ? "black" : userColor,
          board_size: boardSize,
        }),
      });
      router.push(`/game/play/${res.id}`);
    } catch (e: unknown) {
      const code = (e as ApiError).code || "validation";
      if ((e as ApiError).status === 401) {
        router.replace("/login?next=/game/new");
        return;
      }
      toast.error(t(`errors.${code}`));
    } finally {
      setBusy(false);
    }
  };

  if (authed === null) return null;

  return (
    <div className="flex flex-col gap-8 py-6">
      <Hero title={t("game.newGame")} subtitle={t("game.newGameSubtitle")} />

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[2fr_1fr]">
        <div className="flex flex-col gap-8">
          <section className="flex flex-col gap-4">
            <RuleDivider label={t("game.sectionOpponent")} />
            <RankPicker value={rank} onChange={setRank} />
          </section>

          <section className="flex flex-col gap-4">
            <RuleDivider label={t("game.sectionBoard")} />
            <BoardSizePicker value={boardSize} onChange={setBoardSize} />
          </section>

          <section className="flex flex-col gap-4">
            <RuleDivider label={t("game.sectionHandicap")} />
            <HandicapPicker
              boardSize={boardSize}
              value={handicap}
              onChange={setHandicap}
            />
          </section>

          {handicap === 0 && (
            <section className="flex flex-col gap-4">
              <RuleDivider label={t("game.sectionChoice")} />
              <div className="flex flex-col gap-2">
                <Label>{t("game.color")}</Label>
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
              </div>
            </section>
          )}
        </div>

        <aside>
          <Card className="sticky top-4">
            <CardContent className="flex flex-col gap-3 py-4">
              <div className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood">
                {t("game.summary")}
              </div>
              <DataBlock label={t("game.rank")} value={rank} />
              <DataBlock
                label={t("game.boardSize")}
                value={`${boardSize}×${boardSize}`}
              />
              <DataBlock
                label={t("game.handicap")}
                value={handicap === 0 ? t("game.handicapNone") : `${handicap}`}
              />
              {handicap === 0 && (
                <DataBlock
                  label={t("game.color")}
                  value={
                    userColor === "black"
                      ? t("game.colorBlack")
                      : t("game.colorWhite")
                  }
                />
              )}
              <Button
                className="mt-4 w-full"
                size="lg"
                onClick={onCreate}
                disabled={busy}
              >
                {busy ? "…" : t("game.start")}
              </Button>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}

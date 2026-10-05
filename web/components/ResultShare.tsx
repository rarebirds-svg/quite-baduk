"use client";
// 대국 종료 후 결과 공유 줄 — 관전 링크 공유(ShareButtons) + 결과 카드 PNG 저장.
// 커뮤니티(갤러리·오로·타이젬)에 올릴 수 있는 이미지가 자연 유입의 씨앗이 된다.
import { useState } from "react";
import { Image as ImageIcon } from "lucide-react";
import { toast } from "sonner";
import { useT } from "@/lib/i18n";
import { spectateWatchHref } from "@/lib/routes";
import { buildResultCardSvg, svgToPngBlob } from "@/lib/resultCard";
import ShareButtons from "@/components/editorial/ShareButtons";
import { Button } from "@/components/ui/button";

// backend/app/api/spectate.py의 _MIN_EXPOSED_MOVES와 맞춘다 — 이보다 짧은 대국은
// 관전 목록에 노출되지 않아 링크가 404가 되므로 카드 이미지만 제공한다.
export const SHARE_MIN_MOVES = 10;

export interface ResultShareProps {
  gameId: number;
  size: number;
  board: string;
  moveCount: number;
  title: string;
  subtitle: string;
  resultText: string;
  lastMove?: { x: number; y: number } | null;
}

export function ResultShare(props: ResultShareProps) {
  const t = useT();
  const [busy, setBusy] = useState(false);
  const shareable = props.moveCount >= SHARE_MIN_MOVES;
  const url =
    typeof window !== "undefined"
      ? `${window.location.origin}${spectateWatchHref(props.gameId)}`
      : undefined;
  const shareTitle = `${props.title} — ${props.resultText}`;

  const saveImage = async () => {
    setBusy(true);
    try {
      const svg = buildResultCardSvg({
        size: props.size,
        board: props.board,
        title: props.title,
        subtitle: props.subtitle,
        result: props.resultText,
        lastMove: props.lastMove,
      });
      const blob = await svgToPngBlob(svg);
      const file = new File([blob], `inkbaduk-game-${props.gameId}.png`, { type: "image/png" });
      // 모바일은 공유 시트로 바로 커뮤니티 앱에 보낼 수 있다.
      if (
        typeof navigator.share === "function" &&
        typeof navigator.canShare === "function" &&
        navigator.canShare({ files: [file] })
      ) {
        try {
          await navigator.share({ files: [file], title: shareTitle });
          return;
        } catch {
          // 시트를 닫았거나 미지원 — 다운로드로 폴백.
        }
      }
      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = file.name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(href), 1000);
    } catch {
      toast.error(t("game.share.saveFailed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-2 border border-ink-faint px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" onClick={saveImage} disabled={busy} aria-busy={busy || undefined}>
          <ImageIcon size={16} strokeWidth={1.5} aria-hidden />
          {busy ? t("game.share.saving") : t("game.share.saveImage")}
        </Button>
        {shareable && <ShareButtons label={t("game.share.label")} title={shareTitle} url={url} />}
      </div>
      {shareable && (
        <span className="font-sans text-xs text-ink-mute">{t("game.share.linkNote")}</span>
      )}
    </div>
  );
}

"use client";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { KeybindHint } from "@/components/editorial/KeybindHint";
import {
  IconPass,
  IconResign,
  IconUndo,
  IconHint,
  IconScore,
} from "@/components/editorial/icons";
import { useT } from "@/lib/i18n";

export interface GameControlsProps {
  onPass: () => void;
  onResign: () => void;
  onUndo: () => void;
  onHint: () => void;
  onScoreRequest?: () => void;
  disabled?: boolean;
  undosRemaining?: number;
  scoringAvailable?: boolean;
}

export default function GameControls({
  onPass,
  onResign,
  onUndo,
  onHint,
  onScoreRequest,
  disabled,
  undosRemaining,
  scoringAvailable,
}: GameControlsProps) {
  const t = useT();
  const undoDisabled =
    Boolean(disabled) ||
    (typeof undosRemaining === "number" && undosRemaining <= 0);
  const scoreDisabled = Boolean(disabled) || !scoringAvailable;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (disabled) return;
      const target = e.target as HTMLElement | null;
      if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
      const k = e.key.toLowerCase();
      if (k === "p") {
        e.preventDefault();
        onPass();
      }
      if (k === "r") {
        e.preventDefault();
        onResign();
      }
      if (k === "u") {
        e.preventDefault();
        if (!undoDisabled) onUndo();
      }
      if (k === "h") {
        e.preventDefault();
        onHint();
      }
      if (k === "s" && onScoreRequest && !scoreDisabled) {
        e.preventDefault();
        onScoreRequest();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onPass, onResign, onUndo, onHint, onScoreRequest, disabled, undoDisabled, scoreDisabled]);

  const showScoreButton = Boolean(onScoreRequest);
  return (
    <div className="flex flex-col gap-2 border-t border-ink-faint pt-3">
      <div className={`grid gap-2 ${showScoreButton ? "grid-cols-5" : "grid-cols-4"}`}>
        <Button
          onClick={onPass}
          disabled={disabled}
          variant="outline"
          className="flex flex-col h-auto py-3 gap-1"
        >
          <IconPass />
          <span className="font-sans text-xs font-semibold uppercase tracking-label">
            {t("game.pass")}
          </span>
        </Button>
        <Button
          onClick={onUndo}
          disabled={undoDisabled}
          variant="outline"
          className="flex flex-col h-auto py-3 gap-1"
        >
          <IconUndo />
          <span className="font-sans text-xs font-semibold uppercase tracking-label">
            {t("game.undo")}
            {typeof undosRemaining === "number" && (
              <span className="ml-1 font-mono tabular-nums text-ink-mute">
                {undosRemaining}/3
              </span>
            )}
          </span>
        </Button>
        <Button
          onClick={onHint}
          disabled={disabled}
          variant="outline"
          className="flex flex-col h-auto py-3 gap-1 text-oxblood border-oxblood"
        >
          <IconHint />
          <span className="font-sans text-xs font-semibold uppercase tracking-label">
            {t("game.hint")}
          </span>
        </Button>
        {showScoreButton && (
          <Button
            onClick={onScoreRequest}
            disabled={scoreDisabled}
            variant="outline"
            className="flex flex-col h-auto py-3 gap-1 data-[enabled=true]:border-moss data-[enabled=true]:text-moss"
            data-enabled={scoringAvailable ? "true" : "false"}
          >
            <IconScore />
            <span className="font-sans text-xs font-semibold uppercase tracking-label">
              {t("game.requestScoring")}
            </span>
          </Button>
        )}
        <Button
          onClick={onResign}
          disabled={disabled}
          variant="destructive"
          className="flex flex-col h-auto py-3 gap-1"
        >
          <IconResign />
          <span className="font-sans text-xs font-semibold uppercase tracking-label">
            {t("game.resign")}
          </span>
        </Button>
      </div>
      <div className="flex gap-4 justify-center flex-wrap">
        <KeybindHint keys={["P"]} description={t("game.pass")} />
        <KeybindHint keys={["U"]} description={t("game.undo")} />
        <KeybindHint keys={["H"]} description={t("game.hint")} />
        {showScoreButton && (
          <KeybindHint keys={["S"]} description={t("game.requestScoring")} />
        )}
        <KeybindHint keys={["R"]} description={t("game.resign")} />
      </div>
    </div>
  );
}

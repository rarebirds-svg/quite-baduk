"use client";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { KeybindHint } from "@/components/editorial/KeybindHint";
import {
  IconPass,
  IconResign,
  IconUndo,
  IconHint,
} from "@/components/editorial/icons";
import { useT } from "@/lib/i18n";

export interface GameControlsProps {
  onPass: () => void;
  onResign: () => void;
  onUndo: () => void;
  onHint: () => void;
  disabled?: boolean;
}

export default function GameControls({
  onPass,
  onResign,
  onUndo,
  onHint,
  disabled,
}: GameControlsProps) {
  const t = useT();

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
        onUndo();
      }
      if (k === "h") {
        e.preventDefault();
        onHint();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onPass, onResign, onUndo, onHint, disabled]);

  return (
    <div className="flex flex-col gap-2 border-t border-ink-faint pt-3">
      <div className="grid grid-cols-4 gap-2">
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
          disabled={disabled}
          variant="outline"
          className="flex flex-col h-auto py-3 gap-1"
        >
          <IconUndo />
          <span className="font-sans text-xs font-semibold uppercase tracking-label">
            {t("game.undo")}
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
      <div className="flex gap-4 justify-center">
        <KeybindHint keys={["P"]} description={t("game.pass")} />
        <KeybindHint keys={["U"]} description={t("game.undo")} />
        <KeybindHint keys={["H"]} description={t("game.hint")} />
        <KeybindHint keys={["R"]} description={t("game.resign")} />
      </div>
    </div>
  );
}

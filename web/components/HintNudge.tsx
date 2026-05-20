"use client";
// 힌트 발견·적시 권유를 위한 작은 안내 카드. 대국 화면에서 코치마크
// (첫 대국 1회)와 망설임 프롬프트(같은 자리 장고 시) 두 용도로 쓴다.
import { Lightbulb, X } from "lucide-react";

export interface HintNudgeProps {
  message: string;
  /** 액션 버튼 라벨. 없으면 버튼 미표시 (코치마크처럼 안내만). */
  actionLabel?: string;
  onAction?: () => void;
  onDismiss: () => void;
  dismissLabel: string;
}

export function HintNudge({
  message,
  actionLabel,
  onAction,
  onDismiss,
  dismissLabel,
}: HintNudgeProps) {
  return (
    <aside
      className="border border-oxblood bg-paper-deep px-3 py-2 flex items-baseline gap-2 font-sans text-sm"
      aria-live="polite"
    >
      <Lightbulb
        size={14}
        strokeWidth={1.5}
        className="text-oxblood shrink-0 translate-y-0.5"
        aria-hidden
      />
      <span className="text-ink leading-relaxed">{message}</span>
      <div className="ml-auto flex items-baseline gap-2 shrink-0">
        {actionLabel && onAction && (
          <button
            type="button"
            onClick={onAction}
            className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood hover:underline"
          >
            {actionLabel}
          </button>
        )}
        <button
          type="button"
          onClick={onDismiss}
          aria-label={dismissLabel}
          className="text-ink-faint hover:text-ink"
        >
          <X size={14} strokeWidth={1.5} />
        </button>
      </div>
    </aside>
  );
}

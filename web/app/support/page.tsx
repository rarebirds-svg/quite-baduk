"use client";
// Inkbaduk 운영비 후원 페이지 — 익명·계정 없음. 입금 메모로 표시명 전달.
import { useState } from "react";
import { useT } from "@/lib/i18n";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { Button } from "@/components/ui/button";
import supportConfig from "@/data/support-config.json";

interface SupportRowProps {
  label: string;
  value: string;
  hint?: string;
}

function SupportRow({ label, value, hint }: SupportRowProps) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard refused (insecure context, permission) — quietly skip.
    }
  };
  const isPlaceholder = value === "___FILL_IN___" || value === "";
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-ink-faint py-3 last:border-b-0">
      <div className="flex flex-col gap-0.5 min-w-0">
        <span className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
          {label}
        </span>
        <span
          className={
            "font-mono text-sm break-all " +
            (isPlaceholder ? "text-ink-faint italic" : "text-ink")
          }
        >
          {isPlaceholder ? "(준비 중)" : value}
        </span>
        {hint && (
          <span className="font-sans text-xs text-ink-faint leading-relaxed mt-1">
            {hint}
          </span>
        )}
      </div>
      {!isPlaceholder && (
        <Button
          variant="outline"
          size="sm"
          onClick={onCopy}
          className="shrink-0"
          aria-label="복사"
        >
          {copied ? "복사됨" : "복사"}
        </Button>
      )}
    </div>
  );
}

export default function SupportPage() {
  const t = useT();
  const cfg = supportConfig as {
    tossId: string;
    bankName: string;
    bankAccount: string;
    bankOwner: string;
    stripeLink: string;
  };

  return (
    <div className="space-y-6">
      <Hero
        title={t("support.heading")}
        subtitle={t("support.subtitle")}
      />

      <p className="font-sans text-sm text-ink leading-relaxed max-w-prose">
        {t("support.intro")}
      </p>

      <RuleDivider weight="strong" />

      <section className="space-y-4 max-w-prose">
        <h2 className="font-serif text-xl">{t("support.howSection")}</h2>
        <p className="font-sans text-sm text-ink-mute leading-relaxed">
          {t("support.memoHint")}
        </p>

        <div className="border border-ink-faint px-4">
          <SupportRow
            label={t("support.tossLabel")}
            value={cfg.tossId}
            hint={t("support.tossHint")}
          />
          <SupportRow
            label={t("support.bankLabel")}
            value={
              cfg.bankName && cfg.bankAccount
                ? `${cfg.bankName} ${cfg.bankAccount}`
                : ""
            }
            hint={
              cfg.bankOwner && cfg.bankOwner !== "___FILL_IN___"
                ? `${t("support.bankOwnerLabel")} ${cfg.bankOwner}`
                : undefined
            }
          />
          {cfg.stripeLink ? (
            <SupportRow
              label={t("support.stripeLabel")}
              value={cfg.stripeLink}
              hint={t("support.stripeHint")}
            />
          ) : (
            <div className="border-b border-ink-faint py-3 last:border-b-0">
              <span className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
                {t("support.stripeLabel")}
              </span>
              <p className="font-sans text-xs text-ink-faint italic mt-1">
                {t("support.stripePending")}
              </p>
            </div>
          )}
        </div>
      </section>

      <RuleDivider weight="faint" />

      <section className="space-y-3 max-w-prose">
        <h2 className="font-serif text-xl">{t("support.disclaimerSection")}</h2>
        <p className="font-sans text-sm text-ink-mute leading-relaxed">
          {t("support.disclaimerBody")}
        </p>
      </section>

      <RuleDivider weight="faint" />

      <p className="font-sans text-xs text-ink-faint">
        <a
          href="/supporters"
          className="text-oxblood hover:underline"
        >
          {t("support.viewSupporters")} →
        </a>
      </p>
    </div>
  );
}

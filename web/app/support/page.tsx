"use client";
// Inkbaduk 운영비 후원 페이지 — 익명·계정 없음. 입금 메모로 표시명 전달.
import { useState } from "react";
import { useT } from "@/lib/i18n";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { Button } from "@/components/ui/button";
import supportConfig from "@/data/support-config.json";

const PLACEHOLDER = "___FILL_IN___";

function isMissing(v: string | undefined | null): boolean {
  return !v || v === PLACEHOLDER;
}

interface SupportRowProps {
  label: string;
  /** Plain-text value users would copy (e.g., 계좌번호). */
  copyValue?: string;
  /** Outbound link (e.g., 카카오페이 QR 링크, PayPal.me). */
  href?: string;
  /** Visible string under the label — falls back to copyValue or href host. */
  displayValue?: string;
  hint?: string;
  pendingLabel: string;
}

function SupportRow({
  label,
  copyValue,
  href,
  displayValue,
  hint,
  pendingLabel,
}: SupportRowProps) {
  const [copied, setCopied] = useState(false);

  const placeholder = isMissing(copyValue) && isMissing(href);
  const onCopy = async () => {
    if (!copyValue || isMissing(copyValue)) return;
    try {
      await navigator.clipboard.writeText(copyValue);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard refused — quietly skip.
    }
  };

  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-ink-faint py-3 last:border-b-0">
      <div className="flex flex-col gap-0.5 min-w-0">
        <span className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
          {label}
        </span>
        {placeholder ? (
          <span className="font-mono text-sm italic text-ink-faint">
            {pendingLabel}
          </span>
        ) : href && !isMissing(href) ? (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-sm text-oxblood hover:underline break-all"
          >
            {displayValue ?? href}
          </a>
        ) : (
          <span className="font-mono text-sm text-ink break-all">
            {displayValue ?? copyValue}
          </span>
        )}
        {hint && (
          <span className="font-sans text-xs text-ink-faint leading-relaxed mt-1">
            {hint}
          </span>
        )}
      </div>
      {copyValue && !isMissing(copyValue) && (
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
  // 모든 필드는 선택사항으로 다룬다 — JSON 스키마가 운영자 손에 따라
  // 부분만 채워질 수 있고, 누락된 채널은 "(준비 중)"으로 렌더링.
  const cfg = supportConfig as Partial<{
    kakaoPayQr: string;
    bankName: string;
    bankAccount: string;
    bankOwner: string;
    paypalMe: string;
  }>;

  const bankValue =
    !isMissing(cfg.bankName) && !isMissing(cfg.bankAccount)
      ? `${cfg.bankName} ${cfg.bankAccount}`
      : "";
  const bankHint =
    !isMissing(cfg.bankOwner)
      ? `${t("support.bankOwnerLabel")} ${cfg.bankOwner}`
      : undefined;

  return (
    <div className="space-y-6">
      <Hero
        title={t("support.heading")}
        subtitle={t("support.subtitle")}
      />

      <div className="space-y-3 max-w-prose">
        <p className="font-sans text-sm text-ink leading-relaxed">
          {t("support.intro")}
        </p>
        <p className="font-sans text-sm text-ink leading-relaxed">
          {t("support.intro2")}
        </p>
      </div>

      <RuleDivider weight="strong" />

      <section className="space-y-4 max-w-prose">
        <h2 className="font-serif text-xl">{t("support.howSection")}</h2>
        <p className="font-sans text-sm text-ink-mute leading-relaxed">
          {t("support.memoHint")}
        </p>

        <div className="border border-ink-faint px-4">
          <SupportRow
            label={t("support.kakaoPayLabel")}
            href={cfg.kakaoPayQr}
            displayValue={t("support.kakaoPayOpenLink")}
            hint={t("support.kakaoPayHint")}
            pendingLabel={t("support.pending")}
          />
          <SupportRow
            label={t("support.bankLabel")}
            copyValue={bankValue}
            hint={bankHint}
            pendingLabel={t("support.pending")}
          />
          <SupportRow
            label={t("support.paypalLabel")}
            href={cfg.paypalMe}
            displayValue={cfg.paypalMe ? cfg.paypalMe.replace(/^https?:\/\//, "") : ""}
            hint={t("support.paypalHint")}
            pendingLabel={t("support.pending")}
          />
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

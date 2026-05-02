"use client";
import Link from "next/link";
import { BrandMark } from "@/components/editorial/BrandMark";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { useLocale, useT } from "@/lib/i18n";
import ko from "@/lib/i18n/ko.json";
import en from "@/lib/i18n/en.json";

type TermsDict = typeof ko.terms;

const dicts = { ko, en } as const;

const SECTION_ORDER = [
  "intro",
  "account",
  "prohibited",
  "aiDisclaimer",
  "serviceChanges",
  "ip",
  "jurisdiction",
  "contact",
] as const;

export default function TermsPage() {
  const t = useT();
  const [locale] = useLocale();
  const dict: TermsDict = dicts[locale].terms;

  return (
    <div className="mx-auto max-w-3xl px-6 py-12 md:py-16">
      {/* Masthead */}
      <header className="flex items-center justify-between border-b border-ink pb-4">
        <BrandMark size={32} />
        <div className="flex items-baseline gap-3 font-sans text-xs font-semibold uppercase tracking-widest text-ink-mute">
          <span>{t("home.masthead")}</span>
          <span className="text-ink-faint">·</span>
          <span className="font-mono tabular-nums">{t("nav.volume")}</span>
        </div>
      </header>

      {/* Page title */}
      <section className="py-10 md:py-14">
        <p className="font-sans text-xs font-semibold uppercase tracking-widest text-oxblood mb-4">
          {dict.eyebrow}
        </p>
        <h1 className="font-serif italic text-4xl md:text-6xl leading-[1.15] text-ink">
          {dict.title}
        </h1>
        <p className="mt-6 font-sans text-base text-ink-mute leading-relaxed max-w-2xl">
          {dict.intro}
        </p>
      </section>

      <RuleDivider weight="strong" />

      {/* Sections */}
      <div className="mt-10 space-y-10 md:space-y-12">
        {SECTION_ORDER.map((key, idx) => {
          const section = dict.sections[key];
          return (
            <article key={key}>
              <div className="flex items-baseline gap-4 mb-3">
                <span className="font-mono tabular-nums text-xs text-oxblood shrink-0">
                  {String(idx + 1).padStart(2, "0")}
                </span>
                <h2 className="font-serif text-lg md:text-xl text-ink leading-snug">
                  {section.title}
                </h2>
              </div>
              <ul className="list-disc list-inside space-y-1.5 ml-8">
                {section.items.map((item, i) => (
                  <li
                    key={i}
                    className="font-sans text-sm md:text-base text-ink-mute leading-relaxed"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            </article>
          );
        })}
      </div>

      {/* Footer */}
      <div className="mt-14 md:mt-16">
        <RuleDivider weight="faint" />
        <div className="mt-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <p className="font-sans text-xs text-ink-faint">
            {dict.lastUpdated}: {dict.lastUpdatedDate}
          </p>
          <Link
            href="/"
            className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute transition-base hover:text-oxblood"
          >
            ← {dict.backHome}
          </Link>
        </div>
      </div>
    </div>
  );
}

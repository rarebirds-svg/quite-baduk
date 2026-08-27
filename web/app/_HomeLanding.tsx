"use client";
// 홈 랜딩 본문 — i18n 훅과 히어로 글자 크기 자동 맞춤이 필요해 클라이언트로 남긴 조각.
import { useEffect, useRef } from "react";
import { useT } from "@/lib/i18n";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { BoardPreview } from "@/components/editorial/BoardPreview";
import { NewsHook } from "@/components/editorial/NewsHook";
import type { NewsHookData } from "@/lib/newsHook";
import { ClusterLinks } from "@/components/editorial/ClusterLinks";
import QuickStartForm from "@/components/QuickStartForm";

export default function HomeLanding({ newsHook }: { newsHook: NewsHookData | null }) {
  const t = useT();

  // Hero copy is fixed — one message repeated across visits so it can be
  // learned and measured.
  const headline = t("home.hero.heading1");
  const subtitle = t("home.hero.sub1");

  // Auto-fit the hero headline to a single line. Starts at the CSS-declared
  // size and shrinks to the largest size that still fits in the container.
  // Re-runs when the headline text changes, the viewport resizes, or web
  // fonts finish loading (all three can change the measured width).
  const headingRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    const el = headingRef.current;
    if (!el) return;
    const fit = () => {
      // Clear prior inline size so we remeasure from the CSS baseline.
      el.style.fontSize = "";
      const parent = el.parentElement;
      if (!parent) return;
      const maxWidth = parent.clientWidth;
      const baseCs = window.getComputedStyle(el);
      let px = parseFloat(baseCs.fontSize);
      // Safety bounds: never shrink below 22px, cap iterations at 200.
      for (let i = 0; i < 200 && el.scrollWidth > maxWidth && px > 22; i++) {
        px = Math.max(22, px - Math.max(1, px * 0.03));
        el.style.fontSize = `${px}px`;
      }
    };
    // First measure after layout; rerun when fonts finish and on resize.
    const raf = requestAnimationFrame(fit);
    window.addEventListener("resize", fit);
    const fonts = (document as Document & { fonts?: FontFaceSet }).fonts;
    fonts?.ready.then(fit).catch(() => undefined);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", fit);
    };
  }, [headline]);

  return (
    <div className="mx-auto max-w-3xl px-6 py-12 md:py-16">
      {/* Hero — brand identity lives in TopNav, so no masthead here */}
      <section className="pb-14 md:pb-20">
        <p className="font-sans text-xs font-semibold uppercase tracking-widest text-oxblood mb-5">
          {t("home.edition")}
        </p>
        <h1
          ref={headingRef}
          className="break-keep font-serif italic text-4xl leading-[1.15] text-ink sm:whitespace-nowrap sm:text-5xl md:text-7xl"
        >
          {headline}
        </h1>
        <p className="mt-6 md:mt-8 font-sans text-base md:text-lg text-ink-mute max-w-2xl leading-relaxed">
          {subtitle}
        </p>
        <BoardPreview />
        <NewsHook data={newsHook} />
      </section>

      <RuleDivider weight="strong" />

      {/* Quick start — anchored as the call to action */}
      <section id="start" className="mt-10">
        <p className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute mb-3">
          {t("home.scrollHint")}
        </p>
        <QuickStartForm />
        <p className="mt-3 font-sans text-xs text-ink-mute leading-relaxed">
          {t("home.footerNote")}
        </p>
      </section>

      {/* Value props — editorial 3-column lede */}
      <section className="mt-20 md:mt-24">
        <RuleDivider weight="faint" />
        <div className="mt-8 grid grid-cols-1 gap-10 md:grid-cols-3 md:gap-8">
          {[1, 2, 3].map((n) => (
            <article key={n} className="flex flex-col gap-2">
              <span className="font-mono tabular-nums text-xs text-oxblood">
                0{n}
              </span>
              <h2 className="font-serif text-lg text-ink leading-snug">
                {t(`home.valueTitle${n}`)}
              </h2>
              <p className="font-sans text-sm text-ink-mute leading-relaxed">
                {t(`home.valueDesc${n}`)}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* Content cluster — internal links into KataGo/AI-baduk glossary + FAQ.
          Delete this render call (and components/editorial/ClusterLinks.tsx)
          once the Shin Jinseo news cools down and the cluster is retired. */}
      <ClusterLinks />

    </div>
  );
}

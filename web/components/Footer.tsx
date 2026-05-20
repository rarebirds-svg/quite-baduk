"use client";
// 전 페이지 공통 푸터 — InkBaduk 워드마크·정책 링크·저작권을 담는다.
import Link from "next/link";
import { useT } from "@/lib/i18n";
import { BrandMark } from "@/components/editorial/BrandMark";

const FOOTER_LINKS = [
  { href: "/privacy", key: "home.footerPrivacy" },
  { href: "/terms", key: "home.footerTerms" },
  { href: "/support", key: "home.footerSupport" },
] as const;

export default function Footer() {
  const t = useT();
  const year = new Date().getFullYear();

  return (
    <footer className="mt-20 border-t border-ink-faint">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          {/* 워드마크 — 본문 헤더와 같은 BrandMark + serif Inkbaduk */}
          <div className="flex flex-col gap-1.5">
            <Link
              href="/"
              className="flex items-center gap-2"
              aria-label="Inkbaduk"
            >
              <BrandMark size={20} />
              <span className="font-serif text-lg font-semibold tracking-tight text-ink">
                Inkbaduk
              </span>
            </Link>
            <p className="font-sans text-xs text-ink-faint">
              {t("footer.tagline")}
            </p>
          </div>

          {/* 정책·후원 링크 */}
          <nav
            aria-label={t("footer.navLabel")}
            className="flex flex-col gap-2 sm:items-end"
          >
            <ul className="flex flex-wrap gap-x-5 gap-y-2">
              {FOOTER_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute transition-base hover:text-oxblood"
                  >
                    {t(link.key)}
                  </Link>
                </li>
              ))}
            </ul>
            <p className="font-mono text-[11px] tabular-nums text-ink-faint">
              © {year} Inkbaduk · 잉크바둑
            </p>
          </nav>
        </div>
      </div>
    </footer>
  );
}

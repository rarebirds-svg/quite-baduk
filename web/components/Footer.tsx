"use client";
// 전 페이지 공통 푸터 — InkBaduk 워드마크·정책 링크·저작권을 담는다.
import Link from "next/link";
import { useT } from "@/lib/i18n";
import { BrandMark } from "@/components/editorial/BrandMark";
import { IS_APP_SHELL } from "@/lib/appShell";

const ALL_FOOTER_LINKS = [
  { href: "/spectate/pro", key: "home.footerPro" },
  { href: "/glossary", key: "home.footerGlossary" },
  { href: "/faq", key: "home.footerFaq" },
  { href: "/privacy", key: "home.footerPrivacy" },
  { href: "/terms", key: "home.footerTerms" },
  { href: "/support", key: "home.footerSupport" },
];

// 앱 셸 빌드에서 제외되는 웹 전용 경로 — 스토어 정책(/support)과 미포함 라우트.
const WEB_ONLY_HREFS = new Set(["/support", "/supporters", "/glossary", "/faq"]);

export default function Footer() {
  const t = useT();
  const year = new Date().getFullYear();
  const links = IS_APP_SHELL
    ? ALL_FOOTER_LINKS.filter((l) => !WEB_ONLY_HREFS.has(l.href))
    : ALL_FOOTER_LINKS;

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
            <p className="font-sans text-xs text-ink-mute">
              {t("footer.tagline")}
            </p>
          </div>

          {/* 정책·후원 링크 */}
          <nav
            aria-label={t("footer.navLabel")}
            className="flex flex-col gap-2 sm:items-end"
          >
            <ul className="flex flex-wrap gap-x-5 gap-y-2">
              {links.map((link) => (
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
            <p className="font-mono text-[11px] tabular-nums text-ink-mute">
              © {year} Inkbaduk · 잉크바둑
            </p>
          </nav>
        </div>
      </div>
    </footer>
  );
}

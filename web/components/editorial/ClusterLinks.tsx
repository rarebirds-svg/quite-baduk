"use client";
// 홈 랜딩용 카타고·AI 바둑 콘텐츠 클러스터(용어사전·FAQ) 내부 링크 묶음 섹션
import { BookOpen, HelpCircle, Sword, ArrowRight } from "lucide-react";
import { useT } from "@/lib/i18n";
import { RuleDivider } from "@/components/editorial/RuleDivider";

type ClusterLink = {
  href: string;
  labelKey: string;
};

// 신진서-카타고 뉴스 유입용 콘텐츠 클러스터. 뉴스가 식어 페이지를 내릴 때는
// 이 파일과 `app/page.tsx`의 단일 렌더 호출(`<ClusterLinks />`)만 지우면 된다.
const GLOSSARY_LINKS: ClusterLink[] = [
  { href: "/glossary/katago", labelKey: "home.cluster.glossary.katago" },
  { href: "/glossary/alphago", labelKey: "home.cluster.glossary.alphago" },
  { href: "/glossary/ai-baduk", labelKey: "home.cluster.glossary.aiBaduk" },
  { href: "/glossary/human-sl", labelKey: "home.cluster.glossary.humanSl" },
  { href: "/glossary/win-rate", labelKey: "home.cluster.glossary.winRate" },
  { href: "/glossary/ai-jeongseok", labelKey: "home.cluster.glossary.aiJeongseok" },
];

const FAQ_LINKS: ClusterLink[] = [
  { href: "/faq/shin-jinseo-katago", labelKey: "home.cluster.faq.shinJinseo" },
  { href: "/faq/play-against-katago", labelKey: "home.cluster.faq.playAgainst" },
  { href: "/faq/handicap-vs-ai", labelKey: "home.cluster.faq.handicap" },
];

// 실제 검색 유입이 있는 기초 전술 용어 — 홈에서 링크해 랭킹 페이지로 내부 권위 전달.
const BASICS_LINKS: ClusterLink[] = [
  { href: "/glossary/sahwal", labelKey: "home.cluster.basics.sahwal" },
  { href: "/glossary/dansu", labelKey: "home.cluster.basics.dansu" },
  { href: "/glossary/gyega", labelKey: "home.cluster.basics.gyega" },
  { href: "/glossary/handicap", labelKey: "home.cluster.basics.handicap" },
  { href: "/glossary/samsam", labelKey: "home.cluster.basics.samsam" },
];

function LinkGroup({
  icon,
  heading,
  links,
}: {
  icon: React.ReactNode;
  heading: string;
  links: ClusterLink[];
}) {
  const t = useT();
  return (
    <div className="flex flex-col gap-3">
      <h3 className="flex items-center gap-2 font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
        {icon}
        {heading}
      </h3>
      <ul className="flex flex-col divide-y divide-ink-faint border-t border-ink-faint">
        {links.map((link) => (
          <li key={link.href}>
            <a
              href={link.href}
              className="group flex items-center justify-between gap-3 py-3 font-sans text-sm text-ink leading-snug transition-base hover:text-oxblood"
            >
              <span>{t(link.labelKey)}</span>
              <ArrowRight
                size={16}
                strokeWidth={1.5}
                className="shrink-0 text-ink-faint transition-base group-hover:translate-x-0.5 group-hover:text-oxblood"
                aria-hidden="true"
              />
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Two-column bundle of internal links into the KataGo/AI-baduk content
 * cluster (glossary + FAQ), placed on the logged-out home landing to aid
 * discovery and pass internal link authority to the new pages.
 */
export function ClusterLinks() {
  const t = useT();
  return (
    <section className="mt-20 md:mt-24">
      <RuleDivider weight="faint" />
      <div className="mt-8">
        <h2 className="font-serif text-lg text-ink leading-snug">
          {t("home.cluster.heading")}
        </h2>
        <div className="mt-6 grid grid-cols-1 gap-10 md:grid-cols-3 md:gap-12">
          <LinkGroup
            icon={<BookOpen size={16} strokeWidth={1.5} aria-hidden="true" />}
            heading={t("home.cluster.glossaryGroup")}
            links={GLOSSARY_LINKS}
          />
          <LinkGroup
            icon={<Sword size={16} strokeWidth={1.5} aria-hidden="true" />}
            heading={t("home.cluster.basicsGroup")}
            links={BASICS_LINKS}
          />
          <LinkGroup
            icon={<HelpCircle size={16} strokeWidth={1.5} aria-hidden="true" />}
            heading={t("home.cluster.faqGroup")}
            links={FAQ_LINKS}
          />
        </div>
      </div>
    </section>
  );
}

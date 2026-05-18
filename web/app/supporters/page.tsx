"use client";
// 후원자의 벽 — 운영자가 web/data/supporters.json을 수동 갱신.
import { useT } from "@/lib/i18n";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import supportersData from "@/data/supporters.json";

interface Supporter {
  name: string;
  date: string; // ISO YYYY-MM-DD
  note?: string;
}

export default function SupportersPage() {
  const t = useT();
  const supporters = (supportersData.supporters as Supporter[]) ?? [];

  // 월별 그룹핑 (최근 월 먼저)
  const byMonth = new Map<string, Supporter[]>();
  for (const s of supporters) {
    const month = s.date.slice(0, 7); // YYYY-MM
    if (!byMonth.has(month)) byMonth.set(month, []);
    byMonth.get(month)!.push(s);
  }
  const months = Array.from(byMonth.keys()).sort().reverse();

  // 이번 연도 후원자 수
  const thisYear = String(new Date().getFullYear());
  const thisYearCount = supporters.filter((s) => s.date.startsWith(thisYear)).length;

  return (
    <div className="space-y-6">
      <Hero
        title={t("supporters.heading")}
        subtitle={t("supporters.subtitle")}
      />

      <p className="font-sans text-sm text-ink leading-relaxed max-w-prose">
        {t("supporters.intro")}
      </p>

      <RuleDivider weight="strong" />

      {supporters.length === 0 ? (
        <div className="border border-ink-faint p-6 text-center">
          <p className="font-sans text-sm text-ink-mute">
            {t("supporters.empty")}
          </p>
          <p className="font-sans text-xs text-ink-faint mt-2">
            <a href="/support" className="text-oxblood hover:underline">
              {t("supporters.becomeSupporter")} →
            </a>
          </p>
        </div>
      ) : (
        <>
          <p className="font-mono text-sm text-ink-mute">
            {t("supporters.counter")
              .replace("{year}", thisYear)
              .replace("{count}", String(thisYearCount))}
          </p>

          <div className="space-y-6">
            {months.map((m) => (
              <section key={m}>
                <h2 className="font-mono text-xs uppercase tracking-label text-ink-mute border-b border-ink-faint pb-1 mb-3">
                  {m}
                </h2>
                <ul className="space-y-1.5 font-sans text-sm text-ink">
                  {byMonth
                    .get(m)!
                    .sort((a, b) => a.date.localeCompare(b.date))
                    .map((s, i) => (
                      <li
                        key={`${m}-${i}`}
                        className="flex items-baseline gap-3"
                      >
                        <span className="font-mono text-[10px] tabular-nums text-ink-faint shrink-0 w-8">
                          {s.date.slice(8, 10)}.
                        </span>
                        <span className="text-ink">{s.name}</span>
                        {s.note && (
                          <span className="text-ink-faint text-xs italic">
                            — {s.note}
                          </span>
                        )}
                      </li>
                    ))}
                </ul>
              </section>
            ))}
          </div>
        </>
      )}

      <RuleDivider weight="faint" className="my-8" />

      <p className="font-sans text-xs text-ink-faint">
        <a href="/support" className="text-oxblood hover:underline">
          {t("supporters.becomeSupporter")} →
        </a>
      </p>
    </div>
  );
}

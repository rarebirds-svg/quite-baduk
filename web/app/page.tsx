"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuthStore, type Session } from "@/store/authStore";
import { useT } from "@/lib/i18n";
import { BrandMark } from "@/components/editorial/BrandMark";
import { RuleDivider } from "@/components/editorial/RuleDivider";

type CheckResp = { available: boolean; reason?: "taken" | "invalid" };

const HERO_SLOTS = [1, 2, 3, 4, 5] as const;

function pickHeroSlot(): (typeof HERO_SLOTS)[number] {
  return HERO_SLOTS[Math.floor(Math.random() * HERO_SLOTS.length)];
}

export default function NicknameGate() {
  const t = useT();
  const router = useRouter();
  const session = useAuthStore((s) => s.session);
  const setSession = useAuthStore((s) => s.setSession);

  const [nickname, setNickname] = useState("");
  const [status, setStatus] = useState<"idle" | "checking" | "available" | "taken" | "invalid">("idle");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Hero copy rotates: picked at mount so the reader gets variety across
  // visits without jittering while filling out the form. Lazy init avoids
  // running Math.random during SSR (hydration mismatch would flash the
  // fallback copy for a frame).
  const [heroSlot, setHeroSlot] = useState<(typeof HERO_SLOTS)[number] | null>(null);
  useEffect(() => { setHeroSlot(pickHeroSlot()); }, []);

  // If the user already has a live session (came back via existing cookie),
  // skip the form and go straight to the game flow.
  useEffect(() => {
    if (session) router.replace("/game/new");
  }, [session, router]);

  // Debounced availability check.
  useEffect(() => {
    const n = nickname.trim();
    if (!n) { setStatus("idle"); return; }
    setStatus("checking");
    const t = setTimeout(async () => {
      try {
        const r = await api<CheckResp>(`/api/session/nickname/check?name=${encodeURIComponent(n)}`);
        if (r.available) setStatus("available");
        else setStatus(r.reason === "taken" ? "taken" : "invalid");
      } catch {
        setStatus("idle");
      }
    }, 400);
    return () => clearTimeout(t);
  }, [nickname]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) return;
    const n = nickname.trim();
    if (!n) return;
    setError(null);
    setSubmitting(true);
    try {
      const sess = await api<Session>("/api/session", {
        method: "POST",
        body: JSON.stringify({ nickname: n }),
      });
      setSession(sess);
      router.replace("/game/new");
    } catch (e) {
      if (e instanceof ApiError) {
        setError(t(`errors.${e.code === "409" ? "nickname_taken" : e.code === "422" ? "invalid_nickname" : e.code || "validation"}`));
      } else {
        setError(t("errors.validation"));
      }
    } finally {
      setSubmitting(false);
    }
  }

  const hint =
    status === "available" ? t("session.nicknameAvailable") :
    status === "taken" ? t("session.nicknameTaken") :
    status === "invalid" ? t("session.nicknameInvalid") :
    status === "checking" ? "…" : "";

  // Fall back to slot 1 during SSR so there's no layout shift.
  const slot = heroSlot ?? 1;
  const headline = t(`home.hero.heading${slot}`);
  const subtitle = t(`home.hero.sub${slot}`);

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

  const editionTag = useMemo(() => {
    // Tiny decorative "edition number" — stable per mount so it doesn't
    // churn with re-renders but rotates across visits.
    if (heroSlot === null) return "I";
    return ["I", "II", "III", "IV", "V"][heroSlot - 1] ?? "I";
  }, [heroSlot]);

  return (
    <div className="mx-auto max-w-3xl px-6 py-12 md:py-16">
      {/* Masthead */}
      <header className="flex items-center justify-between border-b border-ink pb-4">
        <BrandMark size={32} />
        <div className="flex items-baseline gap-3 font-sans text-xs font-semibold uppercase tracking-widest text-ink-mute">
          <span>{t("home.masthead")}</span>
          <span className="text-ink-faint">·</span>
          <span className="font-mono tabular-nums">No. {editionTag}</span>
        </div>
      </header>

      {/* Hero — randomized headline + subtitle per visit */}
      <section className="py-14 md:py-20">
        <p className="font-sans text-xs font-semibold uppercase tracking-widest text-oxblood mb-5">
          {t("home.edition")}
        </p>
        <h1
          ref={headingRef}
          className="font-serif italic text-5xl md:text-7xl leading-[1.15] text-ink whitespace-nowrap"
        >
          {headline}
        </h1>
        <p className="mt-6 md:mt-8 font-sans text-base md:text-lg text-ink-mute max-w-2xl leading-relaxed">
          {subtitle}
        </p>
      </section>

      <RuleDivider weight="strong" />

      {/* Nickname form — anchored as the call to action */}
      <section className="mt-10">
        <p className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute mb-3">
          {t("home.scrollHint")}
        </p>
        <form onSubmit={submit} className="flex flex-col gap-3 md:flex-row md:items-start">
          <div className="flex-1">
            <input
              autoFocus
              type="text"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              placeholder={t("session.nicknamePlaceholder")}
              maxLength={32}
              className="w-full border border-ink/20 rounded-sm bg-paper px-4 py-3 text-ink text-lg outline-none transition-base focus:border-oxblood"
              aria-describedby="nickname-hint"
              autoComplete="off"
            />
            <p id="nickname-hint" aria-live="polite" className="mt-2 text-sm text-ink-mute min-h-[1.25rem]">
              {hint}
            </p>
            {error && <p role="alert" className="mt-1 text-sm text-oxblood">{error}</p>}
          </div>
          <button
            type="submit"
            disabled={submitting || status !== "available"}
            className="border border-ink bg-ink text-paper rounded-sm px-6 py-3 font-sans text-sm font-semibold uppercase tracking-label transition-base hover:bg-oxblood hover:border-oxblood disabled:opacity-30 disabled:hover:bg-ink disabled:hover:border-ink"
          >
            {t("session.nicknameSubmit")}
          </button>
        </form>
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
              <h3 className="font-serif text-lg text-ink leading-snug">
                {t(`home.valueTitle${n}`)}
              </h3>
              <p className="font-sans text-sm text-ink-mute leading-relaxed">
                {t(`home.valueDesc${n}`)}
              </p>
            </article>
          ))}
        </div>
      </section>

      <footer className="mt-20 pt-6 border-t border-ink-faint">
        <p className="font-sans text-xs text-ink-faint leading-relaxed">
          {t("home.footerNote")}
        </p>
      </footer>
    </div>
  );
}

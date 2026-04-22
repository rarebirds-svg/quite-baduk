"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuthStore, type Session } from "@/store/authStore";
import { useT } from "@/lib/i18n";
import { Hero } from "@/components/editorial/Hero";
import { BrandMark } from "@/components/editorial/BrandMark";
import { RuleDivider } from "@/components/editorial/RuleDivider";

type CheckResp = { available: boolean; reason?: "taken" | "invalid" };

export default function NicknameGate() {
  const t = useT();
  const router = useRouter();
  const session = useAuthStore((s) => s.session);
  const setSession = useAuthStore((s) => s.setSession);

  const [nickname, setNickname] = useState("");
  const [status, setStatus] = useState<"idle" | "checking" | "available" | "taken" | "invalid">("idle");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div className="mx-auto max-w-md py-16">
      <BrandMark size={32} className="mb-6" />
      <Hero
        title={t("session.nicknameHeading")}
        subtitle={t("home.sub")}
      />
      <RuleDivider weight="strong" />
      <form onSubmit={submit} className="mt-8 space-y-4">
        <label className="block">
          <input
            autoFocus
            type="text"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            placeholder={t("session.nicknamePlaceholder")}
            maxLength={32}
            className="w-full border border-ink/10 rounded-sm bg-paper px-3 py-2 text-ink outline-none focus:border-oxblood"
            aria-describedby="nickname-hint"
            autoComplete="off"
          />
        </label>
        <p id="nickname-hint" aria-live="polite" className="text-sm text-ink-mute min-h-[1.25rem]">
          {hint}
        </p>
        {error && <p role="alert" className="text-sm text-oxblood">{error}</p>}
        <button
          type="submit"
          disabled={submitting || status !== "available"}
          className="border border-ink/10 rounded-sm px-5 py-2 bg-paper-deep hover:bg-paper transition-base disabled:opacity-40"
        >
          {t("session.nicknameSubmit")}
        </button>
      </form>
      <p className="mt-10 text-sm text-ink-faint">{t("session.privacyNote")}</p>
    </div>
  );
}

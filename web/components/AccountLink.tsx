"use client";
// 구글 계정 연동(옵트인) 카드 — 설정 화면용. 닉네임 세션은 그대로 두고,
// 전적·기보를 계정에 묶어 다른 기기·만료 뒤에도 이어 볼 수 있게 한다.
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Link2, Unlink } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { IS_APP_SHELL } from "@/lib/appShell";
import { useAuthStore, type Session } from "@/store/authStore";
import { Button } from "@/components/ui/button";

export const GOOGLE_START = "/api/auth/google/start";

export default function AccountLink({ className = "" }: { className?: string }) {
  const t = useT();
  const router = useRouter();
  const params = useSearchParams();
  const session = useAuthStore((s) => s.session);
  const setSession = useAuthStore((s) => s.setSession);
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (IS_APP_SHELL) return; // 앱 셸의 OAuth 리다이렉트는 후속 과제
    api<{ google: boolean }>("/api/auth/providers")
      .then((p) => setEnabled(Boolean(p.google)))
      .catch(() => setEnabled(false));
  }, []);

  // 구글에서 돌아온 결과(?linked=1 / ?link_error=)를 한 번 알리고 URL을 정리한다.
  useEffect(() => {
    const linked = params?.get("linked");
    const err = params?.get("link_error");
    if (!linked && !err) return;
    if (linked) {
      toast.success(t("settings.account.linked"));
      api<Session>("/api/session").then(setSession).catch(() => undefined);
    } else {
      toast.error(t(`settings.account.error_${err}`) === `settings.account.error_${err}`
        ? t("settings.account.error_generic")
        : t(`settings.account.error_${err}`));
    }
    router.replace("/settings");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  if (!enabled || IS_APP_SHELL) return null;
  const account = session?.account ?? null;

  const unlink = async () => {
    setBusy(true);
    try {
      await api("/api/auth/google/unlink", { method: "POST" });
      const me = await api<Session>("/api/session");
      setSession(me);
      toast.success(t("settings.account.unlinked"));
    } catch {
      toast.error(t("settings.account.error_generic"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`flex flex-col gap-2 border border-ink-faint px-4 py-3 ${className}`}>
      <span className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
        {t("settings.account.heading")}
      </span>
      {account ? (
        <>
          <p className="font-sans text-sm text-ink">
            {t("settings.account.linkedAs", { email: account.email ?? "Google" })}
          </p>
          <p className="font-sans text-xs text-ink-mute">{t("settings.account.linkedHint")}</p>
          <Button variant="outline" size="sm" className="self-start" onClick={unlink} disabled={busy}>
            <Unlink size={16} strokeWidth={1.5} aria-hidden />
            {t("settings.account.unlink")}
          </Button>
        </>
      ) : (
        <>
          <p className="font-sans text-xs text-ink-mute">{t("settings.account.hint")}</p>
          <Button asChild size="sm" className="self-start">
            <a href={`${GOOGLE_START}?next=/settings`}>
              <Link2 size={16} strokeWidth={1.5} aria-hidden />
              {t("settings.account.linkGoogle")}
            </a>
          </Button>
        </>
      )}
    </div>
  );
}

"use client";
// 닉네임 게이트 아래의 "이전에 Google로 연동했다면 이어하기" 링크.
// 기능이 켜진 서버(providers.google)에서만, 세션이 없을 때만 보인다.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { IS_APP_SHELL } from "@/lib/appShell";
import { GOOGLE_START } from "@/components/AccountLink";

export default function GoogleContinueLink({ next = "/history" }: { next?: string }) {
  const t = useT();
  const [enabled, setEnabled] = useState(false);
  useEffect(() => {
    if (IS_APP_SHELL) return;
    api<{ google: boolean }>("/api/auth/providers")
      .then((p) => setEnabled(Boolean(p.google)))
      .catch(() => setEnabled(false));
  }, []);
  if (!enabled) return null;
  return (
    <a
      href={`${GOOGLE_START}?next=${encodeURIComponent(next)}`}
      className="self-start font-sans text-sm text-ink-mute underline underline-offset-4 transition-base hover:text-oxblood"
    >
      {t("session.continueWithGoogle")}
    </a>
  );
}

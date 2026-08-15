"use client";
// 랜딩의 원클릭 시작 폼 — 닉네임 한 줄로 세션과 기본 대국을 만들어 대국 화면으로 보낸다.
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { errorMessageKey } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { gamePlayHref } from "@/lib/routes";
import { ensureSession, isNicknameFormatValid, quickStart } from "@/lib/quickStart";
import { useAuthStore } from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function QuickStartForm() {
  const t = useT();
  const router = useRouter();
  const session = useAuthStore((s) => s.session);

  const [nickname, setNickname] = useState("");
  const [busy, setBusy] = useState<"play" | "details" | null>(null);
  const [error, setError] = useState<string | null>(null);
  // 세션이 있으면 닉네임 입력 자체가 없으므로 형식 검증도 건너뛴다.
  const ready = session !== null || isNicknameFormatValid(nickname);
  const formatHint = !session && nickname.trim() !== "" && !ready;

  async function onPlay(e: React.FormEvent) {
    e.preventDefault();
    if (busy || !ready) return;
    setError(null);
    setBusy("play");
    try {
      const id = await quickStart(nickname);
      router.push(gamePlayHref(id));
    } catch (err) {
      setError(t(`errors.${errorMessageKey(err)}`));
      setBusy(null);
    }
  }

  // 비로그인 사용자의 "상세 설정" — /game/new는 세션이 없으면 홈으로 되돌리므로
  // 먼저 세션을 만든 뒤 이동한다.
  async function onDetails() {
    if (busy || !ready) return;
    setError(null);
    setBusy("details");
    try {
      await ensureSession(nickname);
      router.push("/game/new");
    } catch (err) {
      setError(t(`errors.${errorMessageKey(err)}`));
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <form onSubmit={onPlay} className="flex flex-col gap-3 md:flex-row md:items-start">
        {session ? (
          <p className="flex-1 font-sans text-sm text-ink-mute md:py-3">
            {t("quickstart.playingAs", { nickname: session.nickname })}
          </p>
        ) : (
          <div className="flex-1">
            <Input
              autoFocus
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              placeholder={t("session.nicknamePlaceholder")}
              maxLength={32}
              className="h-12 text-base"
              aria-label={t("session.nicknameHeading")}
              aria-describedby="quickstart-hint"
              aria-invalid={formatHint}
              autoComplete="off"
            />
            <p
              id="quickstart-hint"
              aria-live="polite"
              className="mt-2 font-sans text-sm text-ink-mute min-h-[1.25rem]"
            >
              {formatHint ? t("session.nicknameInvalid") : ""}
            </p>
          </div>
        )}
        <Button type="submit" size="lg" disabled={busy !== null || !ready}>
          {busy === "play"
            ? t("quickstart.starting")
            : session
              ? t("quickstart.submitSession")
              : t("quickstart.submit")}
          <ArrowRight size={16} strokeWidth={1.5} aria-hidden />
        </Button>
      </form>

      {error && (
        <p role="alert" className="font-sans text-sm text-oxblood">
          {error}{" "}
          <Link href="/game/new" className="underline underline-offset-4">
            {t("quickstart.retryDetails")}
          </Link>
        </p>
      )}

      {session ? (
        <Link
          href="/game/new"
          className="self-start font-sans text-sm text-ink-mute underline underline-offset-4 transition-base hover:text-oxblood"
        >
          {t("quickstart.details")}
        </Link>
      ) : (
        <Button
          type="button"
          variant="link"
          size="sm"
          className="self-start px-0 text-ink-mute hover:text-oxblood"
          onClick={onDetails}
          disabled={busy !== null || !ready}
        >
          {t("quickstart.details")}
        </Button>
      )}
    </div>
  );
}

"use client";
// 콘텐츠 상세의 공유 줄 — 링크 복사·기기 공유·X 공유(설정 시 카카오톡)를 제공한다.
import { useCallback, useEffect, useState } from "react";
import { Check, Link2, MessageCircle, Share2, X } from "lucide-react";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";

// 카카오 JS SDK는 키가 설정된 환경에서만 주입된다. 기본값은 미설정(버튼 미노출).
const KAKAO_KEY = process.env.NEXT_PUBLIC_KAKAO_JS_KEY;
const KAKAO_SDK_SRC = "https://t1.kakaocdn.net/kakao_js_sdk/2.7.2/kakao.min.js";

type KakaoSdk = {
  isInitialized: () => boolean;
  init: (key: string) => void;
  Share: { sendDefault: (settings: Record<string, unknown>) => void };
};

declare global {
  interface Window {
    Kakao?: KakaoSdk;
  }
}

export default function ShareButtons({
  title,
  url,
  className,
}: {
  title?: string;
  url?: string;
  className?: string;
}) {
  const t = useT();
  // SSR/CSR 마크업을 맞추기 위해 window 의존 값은 마운트 후에 채운다.
  const [href, setHref] = useState(url ?? "");
  const [text, setText] = useState(title ?? "");
  const [canNativeShare, setCanNativeShare] = useState(false);
  const [kakaoReady, setKakaoReady] = useState(false);
  const [status, setStatus] = useState<"idle" | "copied" | "failed">("idle");

  useEffect(() => {
    setHref(url ?? window.location.href);
    setText(title ?? document.title);
    setCanNativeShare(typeof navigator.share === "function");
  }, [url, title]);

  useEffect(() => {
    if (!KAKAO_KEY) return;
    const init = () => {
      const sdk = window.Kakao;
      if (!sdk) return;
      if (!sdk.isInitialized()) sdk.init(KAKAO_KEY);
      setKakaoReady(true);
    };
    if (window.Kakao) {
      init();
      return;
    }
    const script = document.createElement("script");
    script.src = KAKAO_SDK_SRC;
    script.async = true;
    script.onload = init;
    document.head.appendChild(script);
  }, []);

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(href);
      setStatus("copied");
    } catch {
      setStatus("failed");
    }
  }, [href]);

  useEffect(() => {
    if (status === "idle") return;
    const timer = setTimeout(() => setStatus("idle"), 2000);
    return () => clearTimeout(timer);
  }, [status]);

  const nativeShare = useCallback(async () => {
    try {
      await navigator.share({ title: text, url: href });
    } catch {
      // 사용자가 공유 시트를 닫은 경우 — 별도 처리 없음.
    }
  }, [text, href]);

  const kakaoShare = useCallback(() => {
    window.Kakao?.Share.sendDefault({
      objectType: "text",
      text,
      link: { mobileWebUrl: href, webUrl: href },
    });
  }, [text, href]);

  const intentUrl = `https://twitter.com/intent/tweet?url=${encodeURIComponent(
    href,
  )}&text=${encodeURIComponent(text)}`;

  return (
    <div className={cn("not-prose flex flex-wrap items-center gap-2", className)}>
      <span className="font-mono text-[11px] uppercase tracking-label text-ink-faint">
        {t("share.label")}
      </span>

      <Button variant="outline" size="sm" onClick={copy}>
        {status === "copied" ? (
          <Check size={16} strokeWidth={1.5} aria-hidden />
        ) : (
          <Link2 size={16} strokeWidth={1.5} aria-hidden />
        )}
        {status === "copied"
          ? t("share.copied")
          : status === "failed"
            ? t("share.copyFailed")
            : t("share.copyLink")}
      </Button>

      {canNativeShare && (
        <Button variant="outline" size="sm" onClick={nativeShare}>
          <Share2 size={16} strokeWidth={1.5} aria-hidden />
          {t("share.native")}
        </Button>
      )}

      <Button asChild variant="outline" size="sm">
        <a href={intentUrl} target="_blank" rel="noopener noreferrer">
          <X size={16} strokeWidth={1.5} aria-hidden />
          {t("share.x")}
        </a>
      </Button>

      {kakaoReady && (
        <Button variant="outline" size="sm" onClick={kakaoShare}>
          <MessageCircle size={16} strokeWidth={1.5} aria-hidden />
          {t("share.kakao")}
        </Button>
      )}

      <span aria-live="polite" className="sr-only">
        {status === "copied" ? t("share.copied") : status === "failed" ? t("share.copyFailed") : ""}
      </span>
    </div>
  );
}

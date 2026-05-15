"use client";
// 진행 중 대국 페이지에서 다른 화면으로 이탈할 때 컨펌 모달을 띄우기 위한 글로벌 navigation 가드 훅과 헬퍼.
import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

type GuardSlot = {
  active: boolean;
  request: (() => void) | null;
  resolver: ((proceed: boolean) => void) | null;
};

const guard: GuardSlot = {
  active: false,
  request: null,
  resolver: null,
};

export function attemptNavigation(): Promise<boolean> {
  if (!guard.active || !guard.request) return Promise.resolve(true);
  if (guard.resolver) {
    guard.resolver(false);
    guard.resolver = null;
  }
  return new Promise<boolean>((resolve) => {
    guard.resolver = resolve;
    guard.request!();
  });
}

export function resolveNavigation(proceed: boolean) {
  const r = guard.resolver;
  guard.resolver = null;
  r?.(proceed);
}

export function useNavigationGuard({
  when,
  onRequest,
  message,
}: {
  when: boolean;
  onRequest: () => void;
  message?: string;
}) {
  const router = useRouter();
  const onRequestRef = useRef(onRequest);
  onRequestRef.current = onRequest;

  useEffect(() => {
    if (!when) return;

    guard.active = true;
    guard.request = () => onRequestRef.current();

    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = message ?? "";
    };

    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const target = e.target as HTMLElement | null;
      const anchor = target?.closest?.("a");
      if (!anchor) return;
      if (anchor.target && anchor.target !== "" && anchor.target !== "_self") return;
      if (anchor.hasAttribute("download") || anchor.hasAttribute("data-no-guard")) return;
      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) return;
      let url: URL;
      try {
        url = new URL(href, window.location.href);
      } catch {
        return;
      }
      if (url.origin !== window.location.origin) return;
      const samePath =
        url.pathname === window.location.pathname &&
        url.search === window.location.search;
      if (samePath) return;
      e.preventDefault();
      e.stopPropagation();
      attemptNavigation().then((ok) => {
        if (ok) router.push(url.pathname + url.search + url.hash);
      });
    };

    const onPopState = () => {
      window.history.pushState({ __badukGuard: true }, "", window.location.href);
      attemptNavigation().then((ok) => {
        if (ok) window.history.go(-2);
      });
    };

    window.history.pushState({ __badukGuard: true }, "", window.location.href);
    window.addEventListener("beforeunload", onBeforeUnload);
    document.addEventListener("click", onClick, true);
    window.addEventListener("popstate", onPopState);

    return () => {
      guard.active = false;
      guard.request = null;
      const r = guard.resolver;
      guard.resolver = null;
      r?.(false);
      window.removeEventListener("beforeunload", onBeforeUnload);
      document.removeEventListener("click", onClick, true);
      window.removeEventListener("popstate", onPopState);
    };
  }, [when, router, message]);
}

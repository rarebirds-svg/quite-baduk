"use client";
// 앱 셸 네이티브 브리지 — Android 뒤로가기와 포그라운드 복귀를 웹 쪽에 연결한다.
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { IS_APP_SHELL } from "@/lib/appShell";

export const APP_RESUMED_EVENT = "inkbaduk:app-resumed";

export default function AppShellBridge() {
  const router = useRouter();
  useEffect(() => {
    if (!IS_APP_SHELL) return;
    let cleanup: (() => void) | undefined;
    import("@capacitor/app").then(({ App }) => {
      // "/"는 비로그인 게이트, "/game/new"는 로그인 상태의 실질 루트 —
      // AuthGate가 "/"를 "/game/new"로 되밀어 back 트랩이 생기므로 둘 다 최소화 대상.
      const ROOT_PATHS = ["/", "/game/new"];
      const backSub = App.addListener("backButton", () => {
        if (ROOT_PATHS.includes(window.location.pathname)) App.minimizeApp();
        else router.back();
      });
      const stateSub = App.addListener("appStateChange", ({ isActive }) => {
        if (isActive) window.dispatchEvent(new Event(APP_RESUMED_EVENT));
      });
      cleanup = () => {
        backSub.then((s) => s.remove());
        stateSub.then((s) => s.remove());
      };
    });
    // 상태바를 paper 배경에 어두운 아이콘으로 맞춘다 (Editorial 톤).
    // Style.Light = "Dark text for light backgrounds" — 밝은 배경용 어두운 아이콘.
    import("@capacitor/status-bar")
      .then(({ StatusBar, Style }) => StatusBar.setStyle({ style: Style.Light }))
      .catch(() => {});
    return () => cleanup?.();
  }, [router]);
  return null;
}

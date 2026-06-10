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
      const backSub = App.addListener("backButton", () => {
        if (window.location.pathname === "/") App.minimizeApp();
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

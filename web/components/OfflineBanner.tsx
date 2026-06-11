"use client";
// 네트워크 단절 안내 배너 — offline 이벤트 시 상단 고정 표시 (앱 심사 필수 UX).
import { useEffect, useState } from "react";
import { useT } from "@/lib/i18n";
import { IS_APP_SHELL } from "@/lib/appShell";

export default function OfflineBanner() {
  const t = useT();
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    if (IS_APP_SHELL) {
      let remove: (() => void) | undefined;
      import("@capacitor/network").then(async ({ Network }) => {
        const status = await Network.getStatus();
        setOffline(!status.connected);
        const sub = await Network.addListener("networkStatusChange", (s) => {
          setOffline(!s.connected);
        });
        remove = () => {
          void sub.remove();
        };
      });
      return () => remove?.();
    }
    setOffline(!navigator.onLine);
    const on = () => setOffline(false);
    const off = () => setOffline(true);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  if (!offline) return null;

  return (
    <div
      role="status"
      className="fixed inset-x-0 top-0 z-50 bg-oxblood px-4 py-2 text-center text-sm text-paper"
    >
      {t("offline.banner")}
    </div>
  );
}

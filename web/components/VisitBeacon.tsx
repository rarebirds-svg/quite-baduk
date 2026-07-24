"use client";
// 익명 방문을 백엔드로 통보하는 비콘 — 경로 변경마다 1회, 앱셸에서는 비활성.
import { usePathname } from "next/navigation";
import { useEffect } from "react";

import { IS_APP_SHELL } from "@/lib/appShell";

export default function VisitBeacon() {
  const pathname = usePathname();
  useEffect(() => {
    if (IS_APP_SHELL) return;
    if (typeof navigator === "undefined" || !navigator.sendBeacon) return;
    const body = JSON.stringify({ path: pathname, referrer: document.referrer });
    navigator.sendBeacon("/api/analytics/hit", new Blob([body], { type: "application/json" }));
  }, [pathname]);
  return null;
}

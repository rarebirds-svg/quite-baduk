"use client";
// 익명 방문을 백엔드로 통보하는 비콘 — 경로 변경마다 1회, 앱셸에서는 비활성.
import { usePathname } from "next/navigation";
import { useEffect } from "react";

import { IS_APP_SHELL } from "@/lib/appShell";

// 비공개·세션 경로 — 운영자·플레이어 네비게이션이 방문 통계 PV를 부풀리지 않도록 제외.
const PRIVATE_PREFIXES = [
  "/admin", "/game", "/daily", "/history", "/settings", "/dev", "/spectate/watch",
];

export function isPublicPath(path: string): boolean {
  return !PRIVATE_PREFIXES.some((p) => path === p || path.startsWith(p + "/"));
}

export default function VisitBeacon() {
  const pathname = usePathname();
  useEffect(() => {
    if (IS_APP_SHELL) return;
    if (!isPublicPath(pathname)) return;
    if (typeof navigator === "undefined" || !navigator.sendBeacon) return;
    const body = JSON.stringify({ path: pathname, referrer: document.referrer });
    navigator.sendBeacon("/api/analytics/hit", new Blob([body], { type: "application/json" }));
  }, [pathname]);
  return null;
}

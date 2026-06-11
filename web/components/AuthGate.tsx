"use client";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuthStore, type Session } from "@/store/authStore";
import { setSessionToken } from "@/lib/sessionToken";

const PUBLIC_PATHS = new Set(["/", "/privacy", "/terms", "/support", "/supporters"]);
// Content (SEO) route prefixes — viewable without a session, including their
// sub-paths. Crawlers and logged-out visitors can read pro games, themes,
// monthly picks, glossary, and FAQ. Interactive areas (/game, /admin,
// /settings, /history, the live-spectate hub) stay session-gated.
const PUBLIC_PREFIXES = ["/glossary", "/faq", "/spectate/pro", "/spectate/themes", "/spectate/picks"];

export function isPublicPath(pathname: string): boolean {
  if (PUBLIC_PATHS.has(pathname)) return true;
  return PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname() ?? "/";
  const setSession = useAuthStore((s) => s.setSession);
  const session = useAuthStore((s) => s.session);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await api<Session>("/api/session");
        if (!cancelled) setSession(me);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) {
          setSession(null);
          void setSessionToken(null);
          if (!isPublicPath(pathname)) {
            router.replace("/");
            return;
          }
        }
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => { cancelled = true; };
  }, [pathname, router, setSession]);

  // Public path: always render children — even during SSR / before the
  // session check resolves. This is what puts the landing-page body into
  // the initial HTML so search crawlers (notably Naver's Yeti, which is
  // weak at running JS) can index real content instead of a blank shell.
  if (isPublicPath(pathname)) return <>{children}</>;
  // Protected path: block render until the session check resolves, then
  // require a session (the effect above redirects unauthenticated users).
  if (!ready || !session) return null;
  return <>{children}</>;
}

"use client";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuthStore, type Session } from "@/store/authStore";

const PUBLIC_PATHS = new Set(["/"]);

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
          if (!PUBLIC_PATHS.has(pathname)) {
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

  if (!ready) return null;
  // Public path: render either the form (no session) or let the page redirect.
  if (PUBLIC_PATHS.has(pathname)) return <>{children}</>;
  // Protected path: block render until session is resolved.
  if (!session) return null;
  return <>{children}</>;
}

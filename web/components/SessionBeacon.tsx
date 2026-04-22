"use client";
import { useEffect } from "react";

/** Fire-and-forget session end on browser close / tab close.
 *  Paired with server-side idle-purge (1 hour) as a defense in depth. */
export default function SessionBeacon() {
  useEffect(() => {
    const handler = () => {
      try {
        navigator.sendBeacon("/api/session/end");
      } catch {
        // best-effort — the idle purge will pick up orphans within the hour
      }
    };
    window.addEventListener("beforeunload", handler);
    window.addEventListener("pagehide", handler);
    return () => {
      window.removeEventListener("beforeunload", handler);
      window.removeEventListener("pagehide", handler);
    };
  }, []);
  return null;
}

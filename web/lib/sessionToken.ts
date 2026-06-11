// 앱 셸용 세션 토큰 보관소 — 메모리 캐시 + Capacitor Preferences 영속화 담당.
import { IS_APP_SHELL } from "./appShell";

const KEY = "baduk_session_token";
let token: string | null = null;
let hydration: Promise<void> | null = null;

export function getSessionToken(): string | null {
  return token;
}

/** 앱 부팅 후 첫 API 호출 전에 Preferences → 메모리로 1회 복원한다. */
export function ensureSessionToken(): Promise<void> {
  if (!IS_APP_SHELL) return Promise.resolve();
  if (!hydration) {
    hydration = import("@capacitor/preferences")
      .then(async ({ Preferences }) => {
        const { value } = await Preferences.get({ key: KEY });
        if (token === null) token = value;
      })
      .catch(() => {});
  }
  return hydration;
}

export async function setSessionToken(next: string | null): Promise<void> {
  token = next;
  if (!IS_APP_SHELL) return;
  try {
    const { Preferences } = await import("@capacitor/preferences");
    if (next) await Preferences.set({ key: KEY, value: next });
    else await Preferences.remove({ key: KEY });
  } catch {}
}

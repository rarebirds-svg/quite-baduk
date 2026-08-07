import { IS_APP_SHELL } from "./appShell";
import { ensureSessionToken, getSessionToken } from "./sessionToken";

// 웹: 동일 출처 상대경로(next rewrite). 앱 셸: 백엔드 절대 URL 직접 호출.
export const API_BASE = IS_APP_SHELL
  ? (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  : "";

/** 앱 셸에서만 Bearer 헤더를 만든다. 웹은 쿠키가 처리하므로 빈 객체. */
export function authHeaders(): Record<string, string> {
  const t = IS_APP_SHELL ? getSessionToken() : null;
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, public detail?: unknown) {
    super(code);
  }
}

// 인증 실패의 두 가지 원인. 401은 세션 만료(재로그인하면 풀림), 403은 권한 부족.
export type AuthFailure = "expired" | "forbidden";

// Classify an auth failure so callers can tell "log in again" from "you can't
// have this". Returns null for anything that isn't an auth failure — a
// transient 500 must not be mistaken for an expired session.
export function authFailure(e: unknown): AuthFailure | null {
  if (!(e instanceof ApiError)) return null;
  if (e.status === 401) return "expired";
  if (e.status === 403) return "forbidden";
  return null;
}

// i18n key resolver for any thrown error. Keeps catch sites tidy and
// guarantees no raw status code (e.g. "errors.500") ever leaks to the UI.
//
// Convention: backend semantic codes are alphabetic (e.g. "nickname_taken",
// "OCCUPIED") — those are passed through as-is. A purely numeric code means
// `api()` fell back to the HTTP status because the response had no error
// envelope; in that case we map by status range.
export function errorMessageKey(e: unknown): string {
  if (e instanceof ApiError) {
    if (/^\d+$/.test(e.code)) {
      if (e.status >= 500) return "server_error";
      if (e.status === 429) return "rate_limited";
      if (e.status === 401 || e.status === 403) return "forbidden";
      return "validation";
    }
    return e.code;
  }
  return "server_error";
}

export async function api<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  if (IS_APP_SHELL) await ensureSessionToken();
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(init.headers || {}) },
    ...init
  });
  if (!res.ok) {
    let code = String(res.status);
    try {
      const body = await res.json();
      code = body?.error?.code || code;
    } catch {}
    throw new ApiError(res.status, code);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

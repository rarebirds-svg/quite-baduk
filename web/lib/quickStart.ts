// 닉네임 하나로 세션 확보부터 기본 대국 생성까지 처리하는 원클릭 시작 로직.
import { api } from "@/lib/api";
import { setSessionToken } from "@/lib/sessionToken";
import { useAuthStore, type Session } from "@/store/authStore";

const MIN_LEN = 2;
const MAX_LEN = 32;

/** 서버가 최종 검증하므로 여기서는 길이만 본다 — 중복 확인은 하지 않는다. */
export function isNicknameFormatValid(nickname: string): boolean {
  const n = nickname.trim().length;
  return n >= MIN_LEN && n <= MAX_LEN;
}

/** 원클릭 대국의 기본 설정 — 9줄판·9급·호선·흑번. */
export const QUICK_START_GAME = {
  board_size: 9,
  ai_rank: "9k",
  handicap: 0,
  user_color: "black",
} as const;

/** 세션이 없으면 닉네임으로 만들고, 이미 있으면 그대로 쓴다. */
export async function ensureSession(nickname: string): Promise<Session> {
  const { session, setSession } = useAuthStore.getState();
  if (session) return session;
  const created = await api<Session>("/api/session", {
    method: "POST",
    body: JSON.stringify({ nickname: nickname.trim() }),
  });
  await setSessionToken(created.token ?? null);
  setSession(created);
  return created;
}

/**
 * 닉네임 → 세션 → 기본 대국까지 한 번에 만들고 game id를 돌려준다.
 * 실패는 그대로 던져서 호출측이 폴백을 고르게 한다.
 */
export async function quickStart(nickname: string): Promise<number> {
  await ensureSession(nickname);
  const game = await api<{ id: number }>("/api/games", {
    method: "POST",
    body: JSON.stringify(QUICK_START_GAME),
  });
  return game.id;
}

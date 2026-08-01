// 동적 화면 이동 URL 헬퍼 — 웹은 path 세그먼트, 앱 셸은 쿼리 파라미터 형태.
import { IS_APP_SHELL } from "./appShell";

export function gamePlayHref(id: number): string {
  return IS_APP_SHELL ? `/game/play?id=${id}` : `/game/play/${id}`;
}

export function gameReviewHref(id: number): string {
  return IS_APP_SHELL ? `/game/review?id=${id}` : `/game/review/${id}`;
}

export function spectateWatchHref(id: number): string {
  return IS_APP_SHELL ? `/spectate/watch?id=${id}` : `/spectate/${id}`;
}

export function proGameHref(id: number): string {
  return IS_APP_SHELL ? `/spectate/pro/view?id=${id}` : `/spectate/pro/${id}`;
}

// 앱 셸(Capacitor) 빌드 여부 플래그 — NEXT_PUBLIC_APP_SHELL=1 일 때만 true.
export const IS_APP_SHELL = process.env.NEXT_PUBLIC_APP_SHELL === "1";

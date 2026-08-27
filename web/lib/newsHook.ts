// 홈 랜딩 속보 훅 데이터를 web/content/news-hook.json에서 읽는 서버 전용 로더.
import fs from "node:fs";
import path from "node:path";

const NEWS_HOOK_PATH = path.join(process.cwd(), "content", "news-hook.json");

export interface NewsHookData {
  updated_at: string;
  source_url: string;
  body_ko: string;
  body_en: string;
  guide_ko: string;
  guide_en: string;
}

export function getNewsHook(): NewsHookData | null {
  if (!fs.existsSync(NEWS_HOOK_PATH)) return null;
  const raw = fs.readFileSync(NEWS_HOOK_PATH, "utf-8");
  try {
    return JSON.parse(raw) as NewsHookData;
  } catch {
    return null;
  }
}

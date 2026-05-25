// 한글 초성 추출 — 사전/글로서리 필터 chip용.
const CHOSEONG_ALL = [
  "ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ",
] as const;

const TENSE_TO_BASE: Record<string, string> = {
  "ㄲ": "ㄱ",
  "ㄸ": "ㄷ",
  "ㅃ": "ㅂ",
  "ㅆ": "ㅅ",
  "ㅉ": "ㅈ",
};

export const CHOSEONG_BASE = ["ㄱ","ㄴ","ㄷ","ㄹ","ㅁ","ㅂ","ㅅ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"] as const;

export function leadConsonant(text: string): string | null {
  if (!text) return null;
  const code = text.charCodeAt(0);
  if (code < 0xAC00 || code > 0xD7A3) return null;
  const index = Math.floor((code - 0xAC00) / 588);
  const cho = CHOSEONG_ALL[index];
  return TENSE_TO_BASE[cho] ?? cho;
}

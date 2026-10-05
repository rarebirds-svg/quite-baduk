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

/**
 * 받침 유무에 따라 조사를 고른다 — "이창호와", "조훈현과".
 * 한글이 아닌 글자로 끝나면(영문·숫자) 받침 없는 쪽을 쓴다.
 */
export function withJosa(word: string, withBatchim: string, withoutBatchim: string): string {
  const last = word.charCodeAt(word.length - 1);
  if (last < 0xac00 || last > 0xd7a3) return word + withoutBatchim;
  const hasBatchim = (last - 0xac00) % 28 !== 0;
  return word + (hasBatchim ? withBatchim : withoutBatchim);
}

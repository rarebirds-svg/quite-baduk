// 프로 기보 기사명·기전명을 한국어로 표기하기 위한 단방향(영문→한글) 참조 맵과 헬퍼.
import type { Locale } from "@/lib/i18n";

// 영문 기사명 → 한글. (Task 4에서 전량 확장, korean-copy-qa 검증. 불확실 항목은 누락→영문 폴백.)
export const PLAYER_KO: Record<string, string> = {
  "Lee Changho": "이창호",
  "Honinbo Dosaku": "혼인보 도사쿠",
};

// 영문 기전 base → 한글.
export const TOURNAMENT_KO: Record<string, string> = {
  "Chunlan Cup": "춘란배",
  "Fujitsu Cup": "후지쯔배",
  "Ing Cup": "응씨배",
  "LG Cup": "LG배",
  "Samsung Cup": "삼성화재배",
  "Toyota Cup": "도요타배",
  "ACOM Cup": "ACOM배",
  "Agon-Kiriyama Cup": "아곤·기리야마배",
  "Aizu Cup": "아이즈배",
  "Castle Game": "어성기",
  "Teaching game": "지도기",
  "10-game match": "10번기",
  "20-game match": "20번기",
  "30-game match": "30번기",
  "AlphaGo selfplay": "알파고 자가대국",
  "AlphaGo test": "알파고 테스트 대국",
  "Future of Go Summit": "바둑의 미래 서밋",
  "Google DeepMind Challenge Match": "구글 딥마인드 챌린지 매치",
  "All-Japan Hayago Championship": "전일본 속기 선수권",
  "Hikaru no Go chapter 70": "히카루의 바둑 70화",
  "Mission from Ryukyu Islands": "류큐 사절 대국",
};

export function localizePlayer(name: string, locale: Locale): string {
  if (locale === "ko") return PLAYER_KO[name] ?? name;
  return name;
}

export function localizeRank(rank: string | null, locale: Locale): string {
  if (!rank) return "";
  if (locale !== "ko") return rank;
  const m = /^\s*(\d+)\s*[pdPD]\b/.exec(rank);
  return m ? `${m[1]}단` : rank;
}

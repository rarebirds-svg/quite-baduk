// 프로 기보 기사명·기전명을 한국어로 표기하기 위한 단방향(영문→한글) 참조 맵과 헬퍼.
import type { Locale } from "@/lib/i18n";

// 영문 기사명 → 한글. (korean-copy-qa 검증. 불확실 항목은 누락→영문 폴백.)
export const PLAYER_KO: Record<string, string> = {
  // AI
  AlphaGo: "알파고",
  Alphago: "알파고",
  Master: "마스터",

  // 한국 기사
  "An Kukhyun": "안국현",
  "An Sungjoon": "안성준",
  "An Sungjun": "안성준",
  "Byun Sangil": "변상일",
  "Cho Hanseung": "조한승",
  "Cho Hunhyun": "조훈현",
  "Choi Cheolhan": "최철한",
  "Choi Jeong": "최정",
  "Choi Myeonghun": "최명훈",
  "Han Sanghun": "한상훈",
  "Heo Yeongho": "허영호",
  "Kang Dongyun": "강동윤",
  "Kim Jiseok": "김지석",
  "Kim Junghyun": "김정현",
  "Kim Myeonghoon": "김명훈",
  "Lee Changho": "이창호",
  "Lee Donghun": "이동훈",
  "Lee Sedol": "이세돌",
  "Mok Jinseok": "목진석",
  "Park Cheongsang": "박정상",
  "Park Junghwan": "박정환",
  "Park Yeonghun": "박영훈",
  "Seo Bongsoo": "서봉수",
  "Shin Jinseo": "신진서",
  "Shin Minjun": "신민준",
  "Song Taekon": "송태곤",
  "Won Seongjin": "원성진",
  "Yoo Changhyuk": "유창혁",

  // 중국 기사
  "Chang Hao": "창하오",
  "Chen Yaoye": "천야오예",
  "Dang Yifei": "당이페이",
  "Ding Hao": "딩하오",
  "Fan Hui": "판후이",
  "Fan Tingyu": "판팅위",
  "Gu Li": "구리",
  "Gu Zihao": "구쯔하오",
  "Jiang Weijie": "장웨이제",
  "Ke Jie": "커제",
  "Kong Jie": "쿵제",
  "Lian Xiao": "롄샤오",
  "Liao Yuanhe": "랴오위안허",
  "Luo Xihe": "뤄시허",
  "Ma Xiaochun": "마샤오춘",
  "Meng Tailing": "멍타이링",
  "Mi Yuting": "미위팅",
  "Nie Weiping": "녜웨이핑",
  "Piao Wenyao": "퍄오원야오",
  "Shi Yue": "스웨",
  "Tan Xiao": "탄샤오",
  "Tang Weixing": "탕웨이싱",
  "Tuo Jiaxi": "퉈자시",
  "Wang Xi": "왕시",
  "Xie Erhao": "셰얼하오",
  "Xie He": "셰허",
  "Yang Dingxin": "양딩신",
  "Yang Kaiwen": "양카이원",
  "Yu Bin": "위빈",
  "Yu Zhiying": "위즈잉",
  "Zhou Junxun": "저우쥔쉰",
  "Zhou Ruiyang": "저우루이양",

  // 일본 기사
  "Awaji Shuzo": "아와지 슈조",
  "Cho Chikun": "조치훈",
  "Cho U": "조우",
  "Fujisawa Rina": "후지사와 리나",
  "Fujisawa Shuko": "후지사와 슈코",
  "Hane Naoki": "하네 나오키",
  "Honinbo Dosaku": "혼인보 도사쿠",
  "Honinbo Jowa": "혼인보 조와",
  "Honinbo Shusaku": "혼인보 슈사쿠",
  "Honinbo Shuwa": "혼인보 슈와",
  "Ichiriki Ryo": "이치리키 료",
  "Iyama Yuta": "이야마 유타",
  "Kajiwara Takeo": "가지와라 다케오",
  "Kato Masao": "가토 마사오",
  "Kobayashi Koichi": "고바야시 고이치",
  "Kobayashi Satoru": "고바야시 사토루",
  "Kono Rin": "고노 린",
  "Kudo Norio": "구도 노리오",
  "Murakawa Daisuke": "무라카와 다이스케",
  "Otake Hideo": "오타케 히데오",
  "Rin Kaiho": "린카이호",
  "Shibano Toramaru": "시바노 도라마루",
  "Takao Shinji": "다카오 신지",
  "Takemiya Masaki": "다케미야 마사키",
  "Xie Yimin": "셰이민",
  "Yamashita Keigo": "야마시타 게이고",
  "Yoda Norimoto": "요다 노리모토",
  "Yuki Satoshi": "유키 사토시",
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

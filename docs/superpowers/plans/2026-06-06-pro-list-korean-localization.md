# 프로 목록 한국어 표기(기사명·기전명·단) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 한국어 모드에서 프로 기보 목록·상세의 기사명·기전명·단을 한글로 표기하고(영문 폴백), 영어 모드는 영문 원문을 유지한다.

**Architecture:** ko 전용 단방향 참조 맵(`PLAYER_KO`/`TOURNAMENT_KO`)과 헬퍼(`localizePlayer`/`localizeRank`)를 새 데이터 모듈 `web/lib/proLocale.ts`에 두고, 기존 `formatProEvent`를 base-사전 조회로 일반화한다. 컴포넌트는 렌더 시 헬퍼로 변환한다. 매핑 데이터는 모델 생성 후 `korean-copy-qa`로 검증하며 불확실 항목은 누락(영문 폴백)한다.

**Tech Stack:** Next.js 14 · TypeScript · Vitest. 프론트 명령은 `web/`에서. 스펙: `docs/superpowers/specs/2026-06-06-pro-list-korean-localization-design.md`. 모든 신규 `.ts`는 첫 줄 한국어 헤더 주석 필수.

---

## 파일 구조

- Create: `web/lib/proLocale.ts` — `PLAYER_KO`·`TOURNAMENT_KO`·`localizePlayer`·`localizeRank`
- Modify: `web/lib/proEvent.ts` — `formatProEvent` 일반화(`TOURNAMENT_KO` 사용)
- Modify: `web/components/ProGameList.tsx` — 기사명·단 헬퍼 적용
- Modify: `web/app/spectate/pro/[id]/page.tsx` — 기사명·단 헬퍼 적용
- Modify: `web/lib/i18n/ko.json`·`en.json` — 미사용 `spectate.proTournament.*` 제거
- Test: `web/tests/proLocale.test.ts`(신규), `web/tests/proEvent.test.ts`(확장)

---

## Task 1: proLocale.ts — 헬퍼 + 기전 맵 + 기사 시드

**Files:** Create `web/lib/proLocale.ts`; Test `web/tests/proLocale.test.ts`

- [ ] **Step 1: 실패 테스트 작성** — `web/tests/proLocale.test.ts`:

```typescript
// 프로 기보 기사명·단 한글 표기 헬퍼 테스트.
import { describe, it, expect } from "vitest";
import { localizePlayer, localizeRank } from "@/lib/proLocale";

describe("localizePlayer", () => {
  it("ko: 매핑 있으면 한글", () => {
    expect(localizePlayer("Lee Changho", "ko")).toBe("이창호");
    expect(localizePlayer("Honinbo Dosaku", "ko")).toBe("혼인보 도사쿠");
  });
  it("ko: 매핑 없으면 원문", () => {
    expect(localizePlayer("Nonexistent Player", "ko")).toBe("Nonexistent Player");
  });
  it("en: 항상 원문", () => {
    expect(localizePlayer("Lee Changho", "en")).toBe("Lee Changho");
  });
});

describe("localizeRank", () => {
  it("ko: 선행 단 토큰만 한글", () => {
    expect(localizeRank("9p", "ko")).toBe("9단");
    expect(localizeRank("9p, Kisei, Judan, Oza", "ko")).toBe("9단");
    expect(localizeRank("7d", "ko")).toBe("7단");
  });
  it("ko: 비표준/빈값", () => {
    expect(localizeRank("insei", "ko")).toBe("insei");
    expect(localizeRank(null, "ko")).toBe("");
  });
  it("en: 원문", () => {
    expect(localizeRank("9p, Kisei", "en")).toBe("9p, Kisei");
    expect(localizeRank(null, "en")).toBe("");
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd web && npx vitest run tests/proLocale.test.ts`
Expected: FAIL — cannot resolve `@/lib/proLocale`.

- [ ] **Step 3: 구현** — `web/lib/proLocale.ts` 생성. (기사 맵은 Task 4에서 전량 채움; 여기선 테스트가 참조하는 시드 2개만.)

```typescript
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
```
주의: `"All Japan #1"` 기전은 의미 불확실 → 맵에 넣지 않음(영문 폴백). 위 21개만 등록.

- [ ] **Step 4: 통과 확인**

Run: `cd web && npx vitest run tests/proLocale.test.ts`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add web/lib/proLocale.ts web/tests/proLocale.test.ts
git commit -m "feat(pro): 기사명·단 한글 표기 헬퍼 + 기전 맵 (proLocale)"
```

---

## Task 2: proEvent.ts — base 사전 조회로 일반화

**Files:** Modify `web/lib/proEvent.ts`; Test `web/tests/proEvent.test.ts`

- [ ] **Step 1: 실패 테스트 추가** — `web/tests/proEvent.test.ts`에 아래 describe 블록을 추가(기존 테스트 유지). `setLocale`은 기존 파일이 이미 import 중이면 재선언하지 말 것(중복 import 오류 방지). 없을 때만 `import { setLocale } from "@/lib/i18n";` 추가:

```typescript
describe("formatProEvent — 일반 base", () => {
  it("ko: 비-Cup 기전도 한글 (Castle Game)", () => {
    setLocale("ko");
    expect(formatProEvent("Castle Game", null, "ko")).toBe("어성기");
  });
  it("ko: 서수+base+국수 (Agon-Kiriyama)", () => {
    setLocale("ko");
    expect(formatProEvent("32nd Agon-Kiriyama Cup", "4", "ko")).toBe(
      "제32회 아곤·기리야마배 결승 제4국",
    );
  });
  it("ko: 미매핑 base는 원문 폴백", () => {
    setLocale("ko");
    expect(formatProEvent("All Japan #1", null, "ko")).toBe("All Japan #1");
  });
});
```
(주의: `"32nd Agon-Kiriyama Cup"`은 국수 4가 있어 stage가 final로 보강됨 → "결승" 포함.)

- [ ] **Step 2: 실패 확인**

Run: `cd web && npx vitest run tests/proEvent.test.ts`
Expected: FAIL — 현재는 `Cup` 정규식이라 `Castle Game` 미처리, `Agon-Kiriyama`는 TOURNAMENT_KO 미사용으로 원문.

- [ ] **Step 3: 구현** — `web/lib/proEvent.ts` 전체를 다음으로 교체:

```typescript
// 프로 기보 EV(기전)·RO(국수)를 로케일별 표기 문자열로 조립한다.
import { t, type Locale } from "@/lib/i18n";
import { TOURNAMENT_KO } from "@/lib/proLocale";

interface ParsedEvent {
  editionNum?: number;
  base: string;
  baseKo?: string;
  stage?: "final" | "prelim";
}

// "10th Chunlan Cup Final" / "Castle Game" / "Ing Cup, Korean preliminary" 등을 분해.
function parseEvent(event: string): ParsedEvent {
  let rest = event.trim();
  // 선행 서수
  let editionNum: number | undefined;
  const ord = /^(\d+)(?:st|nd|rd|th)\s+/i.exec(rest);
  if (ord) {
    editionNum = Number(ord[1]);
    rest = rest.slice(ord[0].length);
  }
  // 단계 분리
  let stage: "final" | "prelim" | undefined;
  const prelim = /,\s*[^,]*prelim[^,]*$/i.exec(rest);
  if (prelim) {
    stage = "prelim";
    rest = rest.slice(0, prelim.index);
  } else if (/\s+Final\b/i.test(rest)) {
    stage = "final";
    rest = rest.replace(/\s+Final\b.*$/i, "");
  } else {
    rest = rest.replace(/\s+Title\b.*$/i, "");
  }
  const base = rest.trim();
  return { editionNum, base, baseKo: TOURNAMENT_KO[base], stage };
}

// RO 원문에서 후행 정수(국수)를 뽑는다. "Final 2" → 2, "Final" → undefined.
function parseGameNo(round: string | null): number | undefined {
  if (!round) return undefined;
  const m = /(\d+)\s*$/.exec(round.trim());
  return m ? Number(m[1]) : undefined;
}

export function formatProEvent(
  event: string | null,
  round: string | null,
  locale: Locale,
): string {
  if (!event) return "";
  const { editionNum, baseKo, stage } = parseEvent(event);
  const gameNo = parseGameNo(round);

  // 미매핑 기전 — 원문 + 국수만 로케일 접미.
  if (locale !== "ko" || !baseKo) {
    if (gameNo === undefined) return event;
    return locale === "ko"
      ? `${event} ${t("spectate.proGameNo", { n: gameNo })}`
      : `${event} · ${t("spectate.proGameNo", { n: gameNo })}`;
  }

  // ko & 매핑 — 조립. 국수가 있으면 결승 시리즈 함의 → stage 보강.
  const stageKey = stage ?? (gameNo !== undefined ? "final" : undefined);
  const parts = [
    editionNum !== undefined ? t("spectate.proEdition", { n: editionNum }) : null,
    baseKo,
    stageKey ? t(`spectate.proStage.${stageKey}`) : null,
    gameNo !== undefined ? t("spectate.proGameNo", { n: gameNo }) : null,
  ].filter(Boolean);
  return parts.join(" ");
}
```
(`NAME_TO_KEY`·`EVENT_RE` 기반 구버전은 제거됨. en은 baseKo 무관하게 원문+Game N 폴백 경로를 탄다.)

- [ ] **Step 4: 통과 확인 (신규 + 기존 회귀)**

Run: `cd web && npx vitest run tests/proEvent.test.ts`
Expected: 신규 PASS + 기존 6대 컵 테스트도 PASS — TOURNAMENT_KO에 6대 컵이 있어 `제10회 춘란배 결승 제3국` 등 동일 출력. en 케이스("10th Chunlan Cup Final · Game 3")도 동일.

- [ ] **Step 5: 커밋**

```bash
git add web/lib/proEvent.ts web/tests/proEvent.test.ts
git commit -m "feat(pro): formatProEvent를 기전 base 사전 조회로 일반화 (비-Cup 기전 한글화)"
```

---

## Task 3: 컴포넌트 적용 + i18n 정리

**Files:** Modify `web/components/ProGameList.tsx`, `web/app/spectate/pro/[id]/page.tsx`, `web/lib/i18n/ko.json`, `web/lib/i18n/en.json`

- [ ] **Step 1: ProGameList 적용**

`web/components/ProGameList.tsx` import에 추가:
```typescript
import { localizePlayer, localizeRank } from "@/lib/proLocale";
```
(이미 `useLocale`·`formatProEvent` import 됨.)

기사명·단 렌더 블록(현재):
```tsx
                    <span className="font-sans text-sm text-ink">
                      {r.black_player}
                      {r.black_rank && (
                        <span className="text-ink-faint text-xs"> {r.black_rank}</span>
                      )}
                      <span className="text-ink-faint"> vs </span>
                      {r.white_player}
                      {r.white_rank && (
                        <span className="text-ink-faint text-xs"> {r.white_rank}</span>
                      )}
                    </span>
```
교체:
```tsx
                    <span className="font-sans text-sm text-ink">
                      {localizePlayer(r.black_player, locale)}
                      {localizeRank(r.black_rank, locale) && (
                        <span className="text-ink-faint text-xs"> {localizeRank(r.black_rank, locale)}</span>
                      )}
                      <span className="text-ink-faint"> vs </span>
                      {localizePlayer(r.white_player, locale)}
                      {localizeRank(r.white_rank, locale) && (
                        <span className="text-ink-faint text-xs"> {localizeRank(r.white_rank, locale)}</span>
                      )}
                    </span>
```

- [ ] **Step 2: 프로 상세 적용**

`web/app/spectate/pro/[id]/page.tsx` import에 추가:
```typescript
import { localizePlayer, localizeRank } from "@/lib/proLocale";
```
`blackLabel`/`whiteLabel` 조립(현재):
```tsx
  const blackLabel = `${game.black_player}${
    game.black_rank ? ` ${game.black_rank}` : ""
  }`;
  const whiteLabel = `${game.white_player}${
    game.white_rank ? ` ${game.white_rank}` : ""
  }`;
```
교체:
```tsx
  const blackRank = localizeRank(game.black_rank, locale);
  const whiteRank = localizeRank(game.white_rank, locale);
  const blackLabel = `${localizePlayer(game.black_player, locale)}${
    blackRank ? ` ${blackRank}` : ""
  }`;
  const whiteLabel = `${localizePlayer(game.white_player, locale)}${
    whiteRank ? ` ${whiteRank}` : ""
  }`;
```
(이 파일은 `useLocale`로 `locale`을 이미 보유 — 직전 작업에서 추가됨. 없으면 `const [locale] = useLocale();`를 `const t = useT();` 다음 줄에 추가.)

- [ ] **Step 3: i18n 미사용 키 제거**

`web/lib/i18n/ko.json`과 `en.json`의 `spectate` 객체에서 `"proTournament": { … }` 블록을 **삭제**한다(이제 `TOURNAMENT_KO`가 대체). `proEdition`·`proGameNo`·`proStage`는 **유지**.

JSON 유효성: `cd web && node -e "require('./lib/i18n/ko.json');require('./lib/i18n/en.json');console.log('ok')"`.

- [ ] **Step 4: 타입체크·린트·관련 테스트**

Run: `cd web && npm run type-check && npm run lint && npx vitest run tests/proEvent.test.ts tests/proLocale.test.ts`
Expected: 전부 통과. (proEvent가 `spectate.proTournament.*`를 더 이상 참조하지 않으므로 키 삭제 안전.)

- [ ] **Step 5: 커밋**

```bash
git add web/components/ProGameList.tsx "web/app/spectate/pro/[id]/page.tsx" web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "feat(pro): 목록·상세에 기사명·단 한글 표기 적용 + 미사용 i18n 기전키 제거"
```

---

## Task 4: PLAYER_KO 전량 생성 (249, 불확실 누락)

**Files:** Modify `web/lib/proLocale.ts`

DB의 고유 기사명 249개(아래 목록)에 대해 한글 표기를 생성해 `PLAYER_KO`를 채운다. **확신 없는 항목은 넣지 않는다**(영문 폴백). Task 1의 시드 2개도 최종본에 포함.

표기 규칙.
- 한국 기사: 통용 한글명. 예: Lee Changho→이창호, Cho Hunhyun→조훈현, Lee Sedol→이세돌, Shin Jinseo→신진서, Park Junghwan→박정환, Choi Jeong→최정, Kim Jiseok→김지석, Yoo Changhyuk→유창혁, Seo Bongsoo→서봉수.
- 일본 기사: 한글 음차. 예: Honinbo Dosaku→혼인보 도사쿠, Honinbo Shusaku→혼인보 슈사쿠, Cho Chikun→조치훈, Iyama Yuta→이야마 유타, Takemiya Masaki→다케미야 마사키, Kobayashi Koichi→고바야시 고이치, Yoda Norimoto→요다 노리모토, Otake Hideo→오타케 히데오, Rin Kaiho→린카이호, Ichiriki Ryo→이치리키 료, Shibano Toramaru→시바노 도라마루, Fujisawa Rina→후지사와 리나.
- 중국 기사: 통용 표기. 예: Ke Jie→커제, Gu Li→구리, Chang Hao→창하오, Lee(이름 중국식 X), Ma Xiaochun→마샤오춘, Nie Weiping→녜웨이핑, Shi Yue→스웨/스웨(스웨), Tang Weixing→탕웨이싱, Mi Yuting→미위팅, Fan Tingyu→판팅위, Chen Yaoye→천야오예, Zhou Ruiyang→저우루이양, Yang Dingxin→양딩신, Xie Erhao→셰얼하오.
- AI: AlphaGo→알파고, Alphago→알파고, Master→마스터, Magist→마지스트(불확실 시 누락).
- 합작/복수 표기(`A & B`, `A,B,C`)·정체불명은 누락(영문 폴백).
- 불확실하면 누락. 틀린 한글보다 영문이 낫다.

전체 영문 기사명 목록(249):
```
AlphaGo, Alphago, An Kukhyun, An Sungjoon, An Sungjun, Aoki Guseki, Aoki Kikuyo, Arai Chujiro, Awaji Shuzo, Byun Sangil, Chang Hao, Chen Hao, Chen Yaoye, "Chen Yaoye & Zhou Ruiyang & Mi Yuting & Shi Yue & Tang Weixing", Cho Chikun, Cho Hanseung, Cho Hunhyun, Cho Sonjin, Cho U, Choi Cheolhan, Choi Jeong, Choi Myeonghun, Dang Yifei, Ding Hao, Ding Shixiong, Ebizawa Kenzo, Fan Hui, Fan Tingyu, Fang Tingyu, Fujisawa Rina, Fujisawa Shuko, Fujita Kisaburo, Fukuo Genko, Gu Li, "Gu Li & AlphaGo", Gu Zihao, Han Sanghun, Han Yizhou, Hane Naoki, Hattori Hajime, Hattori Seitetsu, Hayashi Hakuei, Hayashi Monnyu, Hayashi Yubi, Heo Yeongho, Higashiyama Chojinbo, Higuchi Tetsuzo, Hinaya Rippo, Hirata Tomoya, Honinbo Doetsu, Honinbo Dosaku, Honinbo Josaku, Honinbo Jowa, Honinbo Sakugen, Honinbo Shusaku, Honinbo Shuwa, Hori Risaburo, Hosenji Hoshin, Hoshiai Hasseki, Hu Yaoyu, Huang Yunsong, Ichiriki Ryo, Imai Hanshichi, Imataki Tarobee, Inoue Dosa Inseki, Inoue Gennan Inseki, Inoue Matsumoto Inseki, Inoue Shutetsu, Ishikawa Otojiro, Itagaki Chuzo, Itagaki Zenbei, Ito Matsujiro, Ito Showa, "Ito Showa,Shusaku", Ito Tokubee, Itsumei Kikyaku, Iyama Yuta, Jiang Weijie, Kadono Chuzaemon, Kadono Kamesaburo, Kajikawa Shurei, Kajiwara Takeo, Kanda Ei, Kang Dongyun, Kato Masao, Kato Ryuwa, Kato Seitetsu, Katsuta Eisuke, Kawai Chodayu, Ke Jie, Kikugawa Yuseki, Kim Jiseok, Kim Junghyun, Kim Myeonghoon, Kimura Genboku, Kishimoto Saichiro, Kobayashi Koichi, Kobayashi Satoru, Kong Jie, Kono Rin, Kudo Norio, Kumagaya Honseki, Kurahashi Masayuki, Kuroda Shunsetsu, Kuwahara Dosetsu, Kuwahara Shusaku, Kyo Kagen, Lee Changho, Lee Donghun, Lee Sedol, Li Qincheng, Li Xiangyu, Li Xuanhao, Lian Xiao, "Lian Xiao & AlphaGo", Liao Yuanhe, Liu Yuhang, Luo Xihe, Ma Xiaochun, Magist, Masaki Shukei, Master, Meng Tailing, Mi Yuting, Mikami Gozan, Minamisato Yohei, Mitamura Kisaburo, Miwa Yoshiro, Miyashita Shuyo, Miyazawa Kichitaro, Mizutani Junsaku, Mizutani Nuiji, Mok Jinseok, Morimoto Ikuemon, Mukai Chiaki, Mukai Shoso, Murakawa Daisuke, Muramatsu Shunsho, Murase Shuho, Murase Yakichi, Mutsuura Yuta, Nagata Jyutoku, Nakagawa Junsetsu, Narabayashi Kurakichi, Nie Weiping, Ninomiya Kaizo, O Keii, O Rissei, Ogawa Doteki, Ogura Doki, Ogura Takami, Okochi Giemon, Okuda Aya, Onizuka Genji, Onkeiji, Ono Genka, Ota Yuzo, Otake Hideo, Ozawa Mitsugoro, Pan Tingyu, Park Cheongsang, Park Junghwan, Park Yeonghun, "Peichin of Hamahiga", Piao Wenyao, Qiao Zhijian, Qiu Jun, Rin Kaiho, Rin Shien, Sakaguchi Sentoku, Sakaguchi Shintaro, Sakai Dotetsu, Sakata Shunosuke, Sanai Tokujiro, Sato Unji, Sekiyama Sendayu, Sendai Jiseibo, Seo Bongsoo, Shi Yue, Shibano Toramaru, Shida Tatsuya, Shin Jinseo, Shin Minjun, Shiraki Sukeemon, Shuto Shun, "Shuwa,Ito Showa,Shusaku", "Shuwa,Sakaguchi Sentoku,Shusaku", Song Taekon, Soya Seijuro, Sugimura Saburozaemon, Suzuki Ayumi, Takahashi Yuseki, Takanashi Seiken, Takao Shinji, Takayama Sanjiro, Takegawa Yasaburo, Takemiya Masaki, Tan Xiao, Tang Weixing, Tokimoto Hajime, Tsuchiya Shuwa, Tsuruoka Saburosuke, "Tsuruoka Saburosuke,Shuwa", Tuo Jiaxi, Udono Tokuzo, Ueno Asami, Wada Ikkei, Wada Kintaro, Wang Haoyang, "Wang Lei (b)", Wang Xi, Won Seongjin, Xie Erhao, Xie He, Xie Ke, Xie Yimin, Yamada Kimio, Yamamoto Kinnosuke, Yamamoto Samutsu, Yamana Eiki, Yamashita Keigo, Yamazaki Dosa, Yamazaki Sotosaburo, Yan Zaiming, Yang Dingxin, Yang Kaiwen, Yasuda Eisai, Yasuda Kinzaburo, Yasuda Shusaku, Yasui Chitetsu, Yasui Sanchi, Yasui Sanchi IX, "Yasui Sanchi IX,Ito Showa,Ota Yuzo", "Yasui Sanchi IX,Sakaguchi Sentoku,Ota Yuzo", Yasui Santetsu II, Yasui Senkaku, Yasui Shunchi, Yoda Norimoto, Yoo Changhyuk, Yoshihara Bunnosuke, Yoshiwa Dogen, Yu Bin, Yu Zhiying, Yuki Satoshi, Yun Chanhee, Zhang Ziliang, Zhou Heyang, Zhou Junxun, Zhou Ruiyang
```

- [ ] **Step 1: 매핑 작성** — 위 규칙에 따라 `PLAYER_KO`를 확신 항목으로 채운다(불확실 누락). 합작/콤마 복수 표기 항목은 모두 누락.

- [ ] **Step 2: 검증 — 빌드/타입/기존 테스트 깨지지 않음**

Run: `cd web && npm run type-check && npx vitest run tests/proLocale.test.ts`
Expected: PASS (시드 테스트 `Lee Changho`/`Honinbo Dosaku` 여전히 유효).

- [ ] **Step 3: 커밋**

```bash
git add web/lib/proLocale.ts
git commit -m "feat(pro): PLAYER_KO 기사명 한글 매핑 전량 생성 (불확실 항목 영문 폴백)"
```

---

## Task 5: korean-copy-qa 검증

**Files:** Modify `web/lib/proLocale.ts` (QA 반영분만)

- [ ] **Step 1: korean-copy-qa 에이전트 호출** — `web/lib/proLocale.ts`의 `PLAYER_KO`·`TOURNAMENT_KO`를 입력으로, 한·중·일 기사명/기전명 표기의 오류·일관성(음차 관례, 통용 표기)·부자연스러움을 점검 요청. 의심 항목은 **제거(영문 폴백)** 권고를 받는다.

- [ ] **Step 2: QA 반영** — 지적된 오표기는 수정, 확신 불가 항목은 `PLAYER_KO`/`TOURNAMENT_KO`에서 삭제(영문 폴백). 시드 테스트(`Lee Changho→이창호`, `Honinbo Dosaku→혼인보 도사쿠`)가 깨지면 안 되므로 이 둘은 검증 통과 가정.

- [ ] **Step 3: 검증**

Run: `cd web && npm run type-check && npx vitest run tests/proLocale.test.ts tests/proEvent.test.ts`
Expected: PASS

- [ ] **Step 4: 커밋**

```bash
git add web/lib/proLocale.ts
git commit -m "fix(pro): korean-copy-qa 검증 반영 — 기사·기전 표기 정정/불확실 폴백"
```

---

## Task 6: 전체 검증

- [ ] **Step 1: 프론트 전체**

Run: `cd web && npm run test -- --run && npm run type-check && npm run lint`
Expected: 전부 PASS. (i18n 파리티 테스트가 `proTournament` 삭제 후에도 ko/en 동일 구조라 통과.)

- [ ] **Step 2: 디자인 토큰 가드**

변경 파일에 하드코딩 hex·이모지 없음(텍스트 로직만). 경고 없을 것.

---

## Self-Review 메모

- **Spec 커버리지**: proLocale 헬퍼+맵(T1)·proEvent 일반화(T2)·컴포넌트+i18n 정리(T3)·PLAYER_KO 전량(T4)·QA 검증(T5)·전체검증(T6) — 스펙 전 항목 매핑.
- **회귀**: T2가 기존 6대 컵 proEvent 출력을 TOURNAMENT_KO로 유지(테스트로 보장). i18n proTournament 삭제는 proEvent가 더 이상 참조 안 하므로 안전(T3 Step4 검증).
- **타입 일관성**: `localizePlayer(name, locale)`·`localizeRank(rank|null, locale)`·`TOURNAMENT_KO`가 T1 정의, T2(proEvent)·T3(컴포넌트)에서 동일 사용.
- **불확실 폴백**: T4·T5가 불확실 항목 누락 → `localizePlayer`/`formatProEvent`의 `?? name`/원문 경로로 영문 표시.
- **데이터 생성**의 한글 값은 모델 생성 + korean-copy-qa 게이트 — 코드 로직은 완결, 데이터는 QA 검증분.
- **배포**: 프론트 빌드 + `com.baduk.web` 재시작 필요(머지 후 단계).

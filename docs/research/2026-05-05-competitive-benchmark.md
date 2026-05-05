# 경쟁 벤치마크 — AI 바둑 (V1.0 출시 전)

- **작성일**: 2026-05-05
- **목적**: iOS/Android 출시 직전, 시장 내 위치와 차별화 포인트 확정
- **방법**: 현 코드베이스 기능 인벤토리(Explore) + 외부 서비스 조사(WebSearch · WebFetch). 메이저 한국 서비스의 2026년 변화를 라이브 검증으로 보강.

---

## 1. 우리 서비스의 현재 상태 (V0.3.x)

### 1.1 기능 인벤토리

| 영역 | 현황 |
|---|---|
| 게임 모드 | vs AI 단독 (사람 vs 사람 없음) |
| AI 강도 | 18급~5단 공개 (UI), 내부적으로 7단까지. visit budget 1~256 |
| AI 인물 | 18명 기사 모델 + 7가지 기풍 (균형/실리/세력/전투/속기/혁신/토종) |
| 보드 | 9×9, 13×13, 19×19. 핸디캡 호선/2~9점 |
| 룰 | 한국식 영역 계가 (호선 덤 0.5, 일반 6.5) |
| 실시간 분석 | 매 수 승률(Black 중심), score lead, ownership 기반 사석 자동 판정 |
| 학습 보조 | 힌트(상위 3수 + 승률·visit), 게임 복기, KataGo 분석 재생 |
| SGF | 내보내기 |
| 인증 | **익명 ephemeral 닉네임** (이메일/소셜 없음). 1시간 idle 만료. |
| 사회 | **없음** — 채팅, 친구, 래더, 관전, 포럼 모두 부재 |
| i18n | 한국어 1급 + 영어. 한국 바둑 용어 완전 정착 |
| 모바일 | 반응형 웹 (Capacitor 셸은 Plan 2 예정) |
| 광고/IAP | **0** (V1.0 무료, PII 미수집) |
| 시간 제한 | **없음** (V1.1+ 의제) |

### 1.2 한 줄 요약

**"광고도 결제도 가입도 없이, KataGo Human-SL과 한국 룰로 한 판 두고 즉시 복기하는 솔로 도장."**

---

## 2. 외부 시장 조사

### 2.1 메이저 한국 상용 (대중·성숙)

#### 오로 바둑 ([cyberoro.com](https://www.cyberoro.com))
- **타깃**: 한국기원 공식 파트너. 진지한 중급~고단 + 프로 관전팬.
- **핵심**: 사람 vs 사람 인증 대국, 프로 기보 DB, 뉴스/생중계.
- **AI (2026 기준)**: **오로 AI 클라우드** 무료 — 대국 중 실시간 승률, 대국 후 AI 복기 ([검증 출처](https://dnublog.co.kr/2026/03/25/%EC%82%AC%EC%9D%B4%EB%B2%84%EC%98%A4%EB%A1%9C-%EB%B0%94%EB%91%91-%EC%95%B1-%EB%8B%A4%EC%9A%B4%EB%A1%9C%EB%93%9C-%EC%82%AC%ED%99%9C%EB%AC%B8%EC%A0%9C-ai-%EB%B3%B5%EA%B8%B0-2026/)).
- **가격**: 무료 가입 + 오로머니(캐시) + 광고. 일부 대국료/강좌는 결제.
- **약점**: 데스크톱 시대 UI 잔재, 모바일 경험 약함, 결제 구조 복잡, 광고 노출.

#### 타이젬 바둑 ([tygem.com](https://www.tygem.com))
- **타깃**: 한·중·일 강자, 강한 상대 매칭 우선.
- **AI (2026 기준)**: **카타고 기반 무료 AI 대국 + AI 복기**. 난이도 조절·추천수·변화도 제공 ([검증 출처](https://ukeeblog.com/%ED%83%80%EC%9D%B4%EC%A0%AC-%EB%B0%94%EB%91%91-%EC%95%B1-%EB%8B%A4%EC%9A%B4%EB%A1%9C%EB%93%9C-%EB%B0%A9%EB%B2%95-2026-%EC%B5%9C%EC%8B%A0-1%EB%B6%84-%EB%A7%8C%EC%97%90-%EC%84%A4%EC%B9%98%ED%95%98/)).
- **가격**: 무료 + 캐시·정기결제(타이젬 클럽), 광고.
- **약점**: 모바일 앱 평가 박함, 회원가입·캐시 압박.

#### 한게임 바둑 ([baduk.hangame.com](https://baduk.hangame.com))
- **타깃**: NHN 통합 ID 캐주얼 유저.
- **AI**: 약식 AI(입문~중급) 보조 메뉴 수준. KataGo 급 분석 부재.
- **가격**: 무료 + 광고 + 한게임 캐시(아바타).
- **약점**: 바둑 카테고리 투자 우선순위 낮음, 광고 헤비.

> **핵심 변화**: 메이저 한국 3사 모두 2026년 시점 KataGo 기반 AI 복기를 무료 또는 사실상 무료로 제공. **"무료 AI 복기"는 더 이상 단독 차별화 무기가 아님**.

### 2.2 글로벌 / 아마추어 서버

| 서비스 | URL | 특징 | 한국어 | 가격 |
|---|---|---|---|---|
| OGS | [online-go.com](https://online-go.com) | 라이브+통신기전, KataGo AI Review | 부분 | 무료 + Site Supporter 구독 |
| KGS | [gokgs.com](https://www.gokgs.com) | 자바 클라이언트, 강좌방, 봇 매칭 | × | 완전 무료 |
| Fox Weiqi (野狐) | [yikeweiqi.com](https://www.yikeweiqi.com) | 글로벌 강자 풀 1위, Golaxy AI | 부분 | 무료 + VIP |
| Pandanet IGS | [pandanet.co.jp](https://www.pandanet.co.jp/) | 일본 통신기전 전통 | × | 기본 무료 |

**우리 카테고리(솔로 AI 대국)와는 축이 다름** — 사람 매칭이 본업. 단, OGS의 AI Review UX는 학습 보조 영역의 벤치마크 가치 있음.

### 2.3 솔로 AI 대국 / 학습 앱 — 직접 경쟁자

#### AI 카타고 바둑 (com.navibarda.katago) — **🚨 가장 가까운 직접 경쟁자**
- **출처**: [App Store](https://apps.apple.com/kr/app/ai-%EC%B9%B4%ED%83%80%EA%B3%A0-%EB%B0%94%EB%91%91/id1560986333), [Google Play](https://play.google.com/store/apps/details?id=com.navibarda.katago)
- **타깃**: 한국 모바일 KataGo 학습 유저
- **플랫폼**: iOS + Android
- **AI**: KataGo 원격 서버 (사용자 GPU 불필요)
- **한국어**: ✅ 1급 ("AI 카타고 바둑")
- **개발사**: YEJUN HAN
- **가격**: **유료** (원격 서버 운영비 사용자 부담)
- **최신 업데이트**: 2024-09 v1.1.17
- **약점**: 유료, 단일 화면 UX, Editorial 톤 부재
- **우리 vs**: **무료 + 익명 + Editorial UX + 인간 기풍 페르소나** 4축으로 차별화 가능

#### BadukAI ([aki65.github.io](https://aki65.github.io/))
- **플랫폼**: Android only
- **언어**: 영어 + 중국어 (한국어 ❌)
- **AI**: KataGo + LeelaZero, 인간형 NN, image-from-camera 보드 인식, joseki memorize
- **가격**: 완전 무료
- **최신**: v1.23.0 (2023-09)
- **약점**: 한국어 부재, iOS 부재, UX 엔지니어 친화 (일반인 진입장벽)
- **우리 vs**: iOS 지원 + 한국어 + 모던 모바일 UX

#### AI Sensei ([ai-sensei.com](https://ai-sensei.com))
- **타깃**: 글로벌 중급 이상 분석 전용 유저
- **기능**: SGF 업로드 → KataGo 자동 복기, 실수 하이라이트, 코치-학생 공유
- **가격**: 무료 한도 + 약 $5/월 구독
- **약점**: 영어 only, 대국 기능 없음 (분석 전용)
- **우리 vs**: **대국 + 즉시 복기를 한 화면에서 무료**

#### KaTrain ([github.com/sanderland/katrain](https://github.com/sanderland/katrain))
- **타깃**: PC 셀프호스팅 KataGo 사용자
- **기능**: 데스크톱 GUI, 강도 슬라이더, 추천수, "teaching games"
- **가격**: 무료 오픈소스 (자체 GPU 필요)
- **약점**: 데스크톱 전용, 설치 부담, 모바일 부재
- **우리 vs**: 모바일 즉시 사용, 한국어 UI

#### Baduk Pop (모바일)
- **타깃**: 입문 캐주얼
- **기능**: 묘수풀이 중심, 일일 챌린지, 9×9 미니 대국
- **약점**: 진지한 대국·실력 향상 한계, 광고·IAP
- **우리 vs**: 무광고 + 진지한 KataGo 강도

#### Study With KataGo ([katagui.baduk.club](https://katagui.baduk.club/))
- 웹 기반 KataGo GUI. 분석 도구 성격, 대국·UX 미흡.

---

## 3. 비교 매트릭스

| 차원 | 오로 | 타이젬 | 한게임 | AI 카타고 바둑 | BadukAI | AI Sensei | KaTrain | **우리** |
|---|---|---|---|---|---|---|---|---|
| 모바일 네이티브 | 약 | 약 | 약 | ✅ | Android만 | ❌(웹) | ❌ | ✅ (Capacitor) |
| 한국어 1급 | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | 부분 | ✅ |
| 광고 없음 | ❌ | ❌ | ❌ | ✅(유료) | ✅ | ✅(부분) | ✅ | ✅ |
| 가입 불필요 | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ |
| 100% 무료 | freemium | freemium | freemium | ❌ | ✅ | freemium | ✅ | ✅ |
| KataGo Human-SL | 일부 | 일부 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 사람 vs 사람 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 즉시 복기 | ✅(2026 무료) | ✅(2026 무료) | △ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Editorial UX | ❌ | ❌ | ❌ | △ | ❌ | △ | ❌ | ✅ |
| 기사 페르소나 | ❌ | ❌ | ❌ | ❌ | △ | ❌ | △ | ✅ (모델만, UI 미노출) |

---

## 4. 카테고리 진단

우리는 **"광고 0 · 익명 · 한국어 1급 · 모바일 네이티브 KataGo Human-SL 솔로 도장"** 카테고리에 위치. 이 정확한 5축 교집합에 **현존 서비스 부재** — 가장 가까운 AI 카타고 바둑조차 유료, BadukAI는 한국어/iOS 부재, 메이저 한국 3사는 광고/캐시/가입 마찰.

### 시장 변화로 사라진 차별화 (재정의 필요)
- ❌ "무료 AI 복기" — 타이젬·오로가 2026년 무료 제공 시작
- ❌ "KataGo 사용" — 메이저 모두 채택

### 살아있는 차별화 (강화)
- ✅ **익명 + 광고 0 + 가입 0** 트라이팩타 — 한국 메이저가 절대 못 따라옴 (수익 모델 충돌)
- ✅ **모바일 네이티브 + Editorial UX** — 한국 메이저는 데스크톱 시대 UI 잔재
- ✅ **한국어 1급** — BadukAI/AI Sensei/KaTrain이 못 채움
- ✅ **iOS + Android 동시** — BadukAI/KaTrain이 못 채움

---

## 5. 추천 특화 기능 (V1.0 → V1.2 로드맵)

우선순위는 (a) 차별화 강도 × (b) 구현 비용 역수.

### Tier S — V1.0 출시 직전 가능

#### S1. 기사 페르소나 카드
- **현황**: 18명 기사 모델 + 7기풍 이미 코드에 존재. UI에선 셀렉터로만 노출.
- **변경**: 기사를 "인물 카드"로 모달 표시. 한 줄 인물 소개("이세돌, 5단", "신진서, 3단"). 한국 정서 강함.
- **비용**: UI/카피 작업만. 프론트 1~2일.
- **차별화**: 한국 메이저는 인물 페르소나 미노출, AI 카타고 바둑·BadukAI도 단순 강도 슬라이더.

#### S2. 수별 실수 하이라이트 + 한 줄 코칭
- **현황**: 매 수 winrate 데이터 있음. 게임 복기 화면도 있음.
- **변경**: winrate drop > 10% 수에 빨간 점 + 한국어 한 줄 ("이 수 -8% 손실. 추천: F4"). "다른 변화도 보기" 1클릭.
- **비용**: 백엔드 0(데이터 있음), 프론트 2~3일.
- **차별화**: AI Sensei가 영어로 잘하는 영역을 한국어로. 한국 메이저는 자동 멘트 없음.

### Tier A — V1.1 (출시 후 첫 업데이트)

#### A1. 익명 친구 대국 (룸 ID 공유)
- **변경**: 6자리 룸코드 생성 → 친구가 코드 입력 → 1:1 대국. ephemeral 모델 유지.
- **비용**: 백엔드 새 라우트 + WS 룸 매니저 (1주일). 프론트 룸 모달 (3일).
- **차별화**: "혼자 두는 도구"에서 "친구와도 두는 도구"로 확장. 가입 강요 없이 사회성 한 단계. 리텐션 핵심.

#### A2. 일일 한 수 챌린지 (turning point)
- **변경**: 누적 게임 DB에서 winrate가 10%+ 흔들린 수를 자동 추출 → 일 1문제. "오늘의 한 수" 푸시 1회.
- **비용**: 백엔드 추출 잡 + 푸시 인프라 (1주). 프론트 화면 (3일).
- **차별화**: Baduk Pop이 게이미피케이션으로 잘하는 영역을 무광고 + 진짜 게임 데이터 기반으로.

### Tier B — V1.2+

#### B1. 카메라 기보 입력
- **변경**: 실물 바둑판 사진 → CV로 좌표 인식 → 디지털 기보 → 즉시 KataGo 분석.
- **비용**: 모바일 카메라 + ONNX/MLKit 보드 detector (2~3주).
- **차별화**: BadukAI가 했지만 한국어/iOS 없음. **한국 시니어 실물 인구**(바둑학원·기원) 흡수 채널.

#### B2. 접근성 모드
- **변경**: 색맹 친화 색상 팔레트, 큰 글씨 모드, 좌표 음성 안내.
- **비용**: 디자인 토큰 + 음성합성 (1주).
- **차별화**: 한국 메이저 빈 공간. Apple/Google 심사에도 호소.

### Tier C — V1.3+ (시장 정착 후)

- **Apple Watch / Wear OS 위젯** — 매일 한 수 챌린지 알림
- **친구 그룹 토너먼트** (룸 코드 4인 풀리그)
- **나만의 기풍 분석** — 사용자의 누적 기보를 KataGo로 메타분석, "당신은 실리형에 가깝습니다" 리포트

---

## 6. 마케팅 카피 후보

- **"광고도 가입도 없는 1인 바둑 도장 — KataGo Human-SL 18급부터 5단까지"**
- "이세돌과 5단으로, 신진서와 3단으로 — 한 판 두고 바로 복기"
- "가입도 결제도 광고도 없이. 그냥 두고, 바로 코칭."

---

## 7. 출처

- [cyberoro.com](https://www.cyberoro.com) · [tygem.com](https://www.tygem.com) · [baduk.hangame.com](https://baduk.hangame.com)
- [online-go.com](https://online-go.com) · [gokgs.com](https://www.gokgs.com) · [yikeweiqi.com](https://www.yikeweiqi.com) · [pandanet.co.jp](https://www.pandanet.co.jp/)
- [AI 카타고 바둑 (App Store)](https://apps.apple.com/kr/app/ai-%EC%B9%B4%ED%83%80%EA%B3%A0-%EB%B0%94%EB%91%91/id1560986333) · [Google Play](https://play.google.com/store/apps/details?id=com.navibarda.katago)
- [BadukAI](https://aki65.github.io/) · [Baduk AI APK](https://m.apkpure.com/baduk-ai/net.kir.baduk_ai)
- [AI Sensei](https://ai-sensei.com) · [KaTrain (GitHub)](https://github.com/sanderland/katrain) · [Study With KataGo](https://katagui.baduk.club/)
- 메이저 한국 서비스 2026 AI 복기 진화 검증: [타이젬](https://ukeeblog.com/%ED%83%80%EC%9D%B4%EC%A0%AC-%EB%B0%94%EB%91%91-%EC%95%B1-%EB%8B%A4%EC%9A%B4%EB%A1%9C%EB%93%9C-%EB%B0%A9%EB%B2%95-2026-%EC%B5%9C%EC%8B%A0-1%EB%B6%84-%EB%A7%8C%EC%97%90-%EC%84%A4%EC%B9%98%ED%95%98/) · [오로](https://dnublog.co.kr/2026/03/25/%EC%82%AC%EC%9D%B4%EB%B2%84%EC%98%A4%EB%A1%9C-%EB%B0%94%EB%91%91-%EC%95%B1-%EB%8B%A4%EC%9A%B4%EB%A1%9C%EB%93%9C-%EC%82%AC%ED%99%9C%EB%AC%B8%EC%A0%9C-ai-%EB%B3%B5%EA%B8%B0-2026/)

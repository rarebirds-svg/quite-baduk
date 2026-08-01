# 신진서-카타고 뉴스 유입 전환 설계

- 날짜: 2026-07-21
- 계기: 2026-07-21 신진서 9단이 카타고(KataGo)와의 3번기(2점 접바둑)에서 2-1 승리. 조선·동아·한겨레·타이젬 등 다수 보도. "알파고 이후 10년만의 인간 승리" 프레이밍으로 화제.
- 목표: "카타고", "신진서", "AI바둑" 관련 검색 수요를 잉크바둑(inkbaduk.com) 유입·대국 전환으로 연결.

## 전략 통찰

뉴스 키워드("신진서 카타고") 자체는 대형 언론이 지배해 바둑 앱이 상위 노출 불가능하다. 정면 승부는 무의미하다. 실효 있는 표적은 뉴스가 만드는 **하류 검색 의도** — "AI랑 바둑 두는 법", "카타고 상대로 바둑", "AI 바둑 사이트" — 이며, 잉크바둑이 바로 KataGo Human-SL 모델과 두는 서비스라 제품 스토리와 정확히 맞는다. "신진서가 상대한 그 카타고, 당신도 지금 마주할 수 있다"로 전환한다.

정확성 원칙. 2점 접바둑·3번기 2-1이라는 사실을 정확히 서술하고 과장하지 않는다.

## 범위 (3개 레버)

### 레버 1 — 콘텐츠 (glossary + FAQ, `web/content/*.md`)

기존 `ai-baduk-vs-human`, `ai-strength-levels` FAQ와 중복을 피해 상호보완적으로 5건만 신설한다.

용어사전(3):
- `katago` — 카타고(KataGo): 오픈소스 최강 바둑 AI, Human-SL 프로필, 신진서 대국 맥락.
- `ai-baduk` — AI 바둑: 알파고→카타고 흐름, 인간 vs AI 구도.
- `human-sl` — 휴먼 SL: 사람 기풍을 학습한 프로필(잉크바둑이 쓰는 모델).

FAQ(2):
- `play-against-katago` — "카타고 상대로 바둑을 둘 수 있나요?" (직접 전환 질의)
- `shin-jinseo-katago` — "신진서가 이긴 카타고, 나도 상대할 수 있나요?" (타임리 질의)

각 항목 하단에 `/game/new` 대국 CTA. frontmatter는 기존 포맷(`slug/kind/title/created_at`) 준수.

### 레버 2 — SEO 배관

- `web/app/robots.ts`: `/spectate` 전체 disallow → 세션 페이지(`/spectate/watch`)만 disallow로 축소, `pro/themes/picks` 색인 개방(현 sitemap↔robots 상충 해소).
- FAQ 인덱스(`web/app/faq/page.tsx` 또는 그 layout)에 `FAQPage` JSON-LD 추가(구글 리치 결과).

### 레버 3 — 홈 히어로 훅

- 홈 랜딩(`web/app/page.tsx` 계열)에 타임리 문구 1줄 + `/game/new` CTA. 디자인 시스템 준수(토큰·이모지 금지·editorial 프리미티브). 나중에 쉽게 내릴 수 있게 격리.

## 실행·검증

1. 콘텐츠 5건 초안 → `docs/ops/content/drafts/` → korean-copy-qa 검토 → 사람 확인 후 `web/content/`로 게시.
2. 코드 3종 → `npm run lint`·`type-check`·`build` → design-token-guardian + visual-qa(홈) → code-reviewer → 사람 확인 후 커밋.
3. 게시·커밋은 검토 통과 후에만.

## 성공 기준

- 5개 콘텐츠가 sitemap에 노출되고 `/game/new` CTA 포함.
- robots 수정으로 `/spectate/pro` 등 색인 개방, build·lint·type-check green.
- 홈 훅이 디자인 토큰 가드 통과, 라이트/다크 시각 회귀 없음.

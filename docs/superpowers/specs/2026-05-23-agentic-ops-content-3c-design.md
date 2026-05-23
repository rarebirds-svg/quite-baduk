# Agentic Ops — 하위 프로젝트 3c: FAQ·용어 해설 LLM 콘텐츠

- 작성일: 2026-05-23
- 상태: 설계 승인 완료, 구현 계획 대기
- 의존: 하위 프로젝트 3a (sitemap·메타), 3b (콘텐츠 라우트 패턴)
- 범위: inkbaduk의 **교육성 LLM 콘텐츠**(글로서리·FAQ) 자동 초안 + 승인 게시

## 배경

3a/3b가 프로기보 메타·테마·픽 페이지를 만들었지만, 검색 유입의 큰 한 축은 "단·급",
"계가", "축", "AI 바둑이 사람과 어떻게 다른가" 같은 **교육성 검색**이다. 3c는
LLM이 그 답을 매주 1개씩 자율적으로 초안하고 사람 승인 후 게시하는 흐름을 만든다.

### 현재 상태

- `.claude/agents/korean-copy-qa.md`가 이미 한국어/Go 용어 QA 에이전트로 정의됨 — 재사용.
- 자율성 정책: "콘텐츠 초안" 🟢 자율, "라이브 게시" 🟡 승인.
- 시드 토픽 부재. 사용자 정의 필요.

### 결정된 설계 축

- **저장**: 마크다운 in-repo (`web/content/{glossary,faq}/<slug>.md`). DB 아님.
  3a/3b의 정적·SEO-native 패턴과 일관, 새 인프라 0.
- **생성**: LLM 자율 초안 (1주 1개 한정).
- **게시**: Telegram 승인 후 agent commit → 사람 push + deploy.

## 접근 — A (마크다운 in-repo + LLM 자율 초안 + Telegram 승인)

- A. **마크다운 + 자율 초안 + 승인 게시 (채택)** — 기존 dev-cycle/telegram-protocol
  핸드오프 모델 재사용. 새 launchd 작업 1개 + 렌더 라우트 + sitemap 확장.
- B. DB-backed + admin UI — content_pages 테이블 + 관리 라우트. 게시 시 deploy
  불필요하나 schema·UI 부담.
- C. LLM 배제 사람만 작성 — 3c의 LLM 콘텐츠 목적과 충돌.

## 설계

### 섹션 1 — 시드 토픽 목록

`docs/ops/content/seed-glossary.yml` + `seed-faq.yml` — 사람이 시작 토픽 15-20개 정의.
각 항목 `{slug, title, prompt_hint}` 만 채우면 LLM이 본문 생성한다.

**초기 글로서리 시드 (10개 정도)** — slug : 제목 예시:
- `dan-gup` : 단·급
- `gyega` : 계가·집
- `pae` : 패
- `chuk` : 축
- `bik` : 빅
- `samsam` : 삼삼
- `komi` : 덤(komi)
- `handicap` : 접바둑·치수
- `hwajeom` : 화점
- `kasaeng` : 사활

**초기 FAQ 시드 (5-10개)**:
- "AI 바둑은 사람과 어떻게 다른가요?"
- "복기·승부처 분석은 무엇인가요?"
- "닉네임 세션이란?"
- "한국 규칙 vs 일본 규칙 차이는?"
- "단을 얻으려면 어떻게 두면 되나요?"

### 섹션 2 — LLM 초안 생성 파이프라인

**자율 사이클** — sub-project 2 `dev-cycle`과 동일 launchd 패턴.

- `com.inkbaduk.content-draft` launchd 작업 — 매주 토요일 02:00 (백업·dev-cycle과 안 겹침)
- 헤드리스 Claude 세션이 `docs/ops/content-draft-prompt.md` 지시문 실행:
  1. 시드 YAML 2개를 읽어 "본문 미작성"(=`web/content/`에 파일 없는) 슬러그 1개 선택.
     우선순위: 글로서리 먼저, FAQ 그 다음. 알파벳 순.
  2. LLM 본문 생성 — 300-600자, 마크다운, 한국어. 출처 표시(예: "위키백과 바둑 항목 요약").
  3. `docs/ops/content/drafts/<slug>.md`에 저장 (frontmatter + 본문).
  4. `korean-copy-qa` 서브에이전트로 자율 QA → 코멘트/수정 반영.
  5. `pending-approvals.md`에 AP 항목 등록 + Telegram 제안 (sub-project 0의
     telegram-protocol 형식).
- **1주기 1개 한정** — 양산 방지. 검증 기간을 거친 후 cadence 조정 가능.

### 섹션 3 — 승인 + 게시

승인 답신 도착 시 (sub-project 0의 telegram-protocol):

1. `docs/ops/content/drafts/<slug>.md`를 `web/content/<type>/<slug>.md`로 이동
   (type은 frontmatter의 `kind: glossary|faq`로 분기).
2. git commit (agent가 자율, push는 사용자) — sub-project 2의 dev-cycle 핸드오프와 동일.
3. 이슈/AP 항목 큐에서 제거, `state/log/`에 기록.
4. 사용자가 push + deploy.md 절차 → prod 반영.

### 섹션 4 — 웹 라우트 + sitemap

- `web/lib/content.ts` — `web/content/{kind}/` 디렉터리를 스캔해 슬러그·메타데이터·body 반환하는 헬퍼.
- `web/app/glossary/[slug]/page.tsx` + `layout.tsx`(generateMetadata) — 마크다운 렌더.
- `web/app/glossary/page.tsx` — 글로서리 인덱스(모든 슬러그 리스트).
- `web/app/faq/[slug]/page.tsx` + `layout.tsx` + `web/app/faq/page.tsx` — 동일 패턴.
- 3a의 `web/app/sitemap.ts` 확장 — 글로서리·FAQ 슬러그를 디렉터리 스캔으로 동적 추가.
  `priority: 0.5`, `changeFrequency: monthly`.

마크다운 렌더는 `remark` + `remark-html` 등 가벼운 파이프라인 사용. 기존 deps에 없으면
`marked` 단일 의존성 추가(작고 검증된 lib).

### 섹션 5 — 범위 경계

**포함** — 시드 YAML 2개 + 초기 시드 15-20개, content-draft launchd + 프롬프트,
마크다운 렌더 라우트 4개(glossary/faq × 상세/인덱스), sitemap 확장.

**제외** — 무한 자동 생성(주 1개 한정), 자동 게시(승인 필수), 다국어(한국어 우선,
영어 deferred), 이미지·다이어그램 생성, admin UI, 시드 토픽 자율 추가(사람이 YAML
편집).

## 검증 기준

이 4가지가 실제 명령 실행으로 통과하면 하위 프로젝트 3c 완료. 문서만으로 완료 선언 금지.

1. 시드 YAML 2개 + 초기 시드 ≥15개 정의됨.
2. `com.inkbaduk.content-draft` launchd 등록 + 수동 트리거로 시드 1개 초안 생성됨
   (`drafts/<slug>.md` 생성, korean-copy-qa QA 통과, Telegram AP 제안 도달).
3. 승인 후 `web/content/<kind>/<slug>.md` 생성 + git commit 1개. 사용자가 push만
   하면 PR/머지 가능 상태.
4. staging에서 `/glossary/<slug>` + `/faq/<slug>` 200 + generateMetadata 고유 메타 +
   sitemap에 슬러그 포함.

## 리스크와 완화

| 리스크 | 완화 |
|---|---|
| LLM이 부정확한 Go 용어 작성 | korean-copy-qa 자율 QA + 사람 승인 게이트 |
| 양산으로 사람 검토 부담 폭증 | 주 1개 한정 launchd. 시드 다 처리되면 자동 휴면 |
| 초안 디렉터리가 git에 누적 | drafts 폴더는 처리 후 published로 move, dangling 정리는 다음 사이클 |
| 마크다운 렌더 XSS | server-side 렌더 + 신뢰된 입력(agent draft + 승인)이라 사용자 입력 아님. 표준 marked로 충분 |
| 동일 슬러그 중복 생성 | 파이프라인 1단계에서 `web/content/`에 파일 존재 시 skip |

## 다음 단계

이 spec 승인 후 `writing-plans` 스킬로 하위 프로젝트 3c의 구현 계획 작성. sub-project 4
(지원·분석팀)는 별도 사이클.

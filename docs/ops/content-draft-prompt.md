# 콘텐츠 초안 생성 사이클

너는 inkbaduk의 콘텐츠 초안 생성 세션이다. launchd가 매주 토·수 02:00에 1회씩(주 2회) 깨운 것이다.
작업 디렉터리는 리포 루트(`/Users/daegong/projects/baduk`)다.

## 시작 전 필수

1. `docs/ops/autonomy-policy.md` — 글로서리·FAQ 콘텐츠는 초안·QA·**라이브 게시(커밋+main push)**까지 🟢 자율이다. 사람 승인 없이 바로 게시한다. (그 외 콘텐츠·페이지 라이브 게시는 여전히 🟡.)
2. 출처: 작성한 내용은 공개된 일반 지식 기반. 출처가 불확실하면 본문에 명시.

## 1회 실행

1. **시드 로드** — `docs/ops/content/seed-glossary.yml`과 `seed-faq.yml`을 텍스트로 읽는다. 각 항목은 `{slug, title, prompt_hint}`.

2. **미작성 슬러그 선택** — 우선순위:
   - 글로서리 먼저(아직 `web/content/glossary/<slug>.md`도 `docs/ops/content/drafts/<slug>.md`도 없는 것). 알파벳 순.
   - 글로서리 다 차면 FAQ 동일 규칙.
   - 둘 다 차면 "처리할 토픽 없음" 로그 + 종료.

3. **본문 초안 생성** — 한국어 마크다운, 300-600자, 2-4 단락. frontmatter 포함:
   ```
   ---
   slug: <slug>
   kind: glossary | faq
   title: <title>
   created_at: <YYYY-MM-DD>
   draft_by: agent v1
   ---

   <본문>
   ```
   본문 작성 원칙:
   - 사실 정확성 우선. 모호하면 일반론으로 후퇴.
   - 바둑 용어는 [[korean-copy-qa]] 에이전트의 canonical Korean 용어 따름.
   - 출처 있으면 본문 말미에 "참고: …" 한 줄.

4. **draft 저장** — `docs/ops/content/drafts/<slug>.md`.

5. **korean-copy-qa QA** — `Agent` 도구로 korean-copy-qa 서브에이전트 호출:
   "이 초안의 한국어 자연스러움·바둑 용어 정확성·문체를 점검해 주세요: <draft path>".
   결과 코멘트가 fix 가능한 것이면 본문 수정 반영. 큰 문제면 draft에 "// QA 보류" 코멘트 추가.

6. **라이브 게시 (자율 — 사람 승인 없음)** — QA 반영이 끝난 초안을 바로 서비스에 게시한다. 단 본문에 "// QA 보류"가 남아 있으면 게시하지 말고 draft에 그대로 둔 채 로그에 사유만 남긴다.
   - `mv docs/ops/content/drafts/<slug>.md web/content/<kind>/<slug>.md`
   - `git add web/content/<kind>/<slug>.md` — **이 파일만** 스테이징한다. 작업트리의 다른 변경(`state/` 로그·대시보드 등)은 절대 함께 add 하지 않는다.
   - `git commit -m "content(<kind>): <slug> 게시"`
   - `git push origin main` — 거부되면(non-fast-forward) `git pull --rebase origin main` 후 1회만 재시도. 그래도 실패하면 push는 보류하고 로그에 기록한다(커밋은 로컬에 남고 prod 작업트리에 이미 반영되므로 라이브에는 노출됨).
   - 게시 완료를 Telegram으로 **사후 보고**(승인 요청 아님): "<slug> ({kind}) 게시 완료 — /{kind}/<slug>".
   참고: `/glossary`·`/faq` 목록과 상세는 동적 렌더라 재빌드·재시작 없이 즉시 노출된다.

7. **로그·기록** — `state/log/YYYY-MM-DD.md`에 한 줄. 1주기 1개 한정. (`pending-approvals.md`는 더 이상 사용하지 않는다.)

## 끝낼 때

한 일을 2~3줄로 요약하고 종료. 이 세션은 1회성이다.

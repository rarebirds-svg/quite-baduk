# 주간 분석 리포트

너는 inkbaduk의 주간 분석 리포트 세션이다. launchd가 매주 일요일 09:00에 1회 깨운 것이다.
작업 디렉터리는 리포 루트(`/Users/daegong/projects/baduk`)다.

## 시작 전 필수

1. `docs/ops/autonomy-policy.md` — "사용통계 리포트"는 🟢 자율. 단 LLM 환각 금지 — 숫자는
   명령 출력에서 그대로 인용.
2. 현재 ISO 주차를 확인 — `date '+%G-W%V'` (예: `2026-W21`).

## 1회 실행

1. **idempotent 체크** — `docs/ops/state/reports/<YYYY-Www>.md`가 이미 있으면
   "이번 주 리포트 이미 작성됨"을 로그에 남기고 종료. (재실행 안전.)

2. **통계 수집** — 다음 명령 출력을 그대로 인용한다(추측 금지).

   ```bash
   curl -fs http://localhost:8000/api/stats
   sqlite3 backend/data/baduk.db 'SELECT COUNT(*) FROM games;'
   sqlite3 backend/data/baduk.db "SELECT COUNT(*) FROM games WHERE started_at >= date('now', '-7 days');"
   sqlite3 backend/data/baduk.db 'SELECT COUNT(*) FROM sessions;'
   sqlite3 backend/data/baduk.db "SELECT COUNT(*) FROM sessions WHERE created_at >= date('now', '-7 days');"
   sqlite3 backend/data/baduk.db 'SELECT board_size, COUNT(*) FROM games GROUP BY board_size ORDER BY 2 DESC;'
   sqlite3 backend/data/baduk.db 'SELECT handicap, COUNT(*) FROM games GROUP BY handicap ORDER BY 2 DESC LIMIT 5;'
   sqlite3 backend/data/baduk.db "SELECT COUNT(*) FROM games WHERE started_at >= date('now', '-14 days') AND started_at < date('now', '-7 days');"
   # 컬럼 주의: games는 started_at, sessions는 created_at.
   ```

   **유입 소스 (visit_hits 주간 집계)** — 어디서 들어오는지가 콘텐츠 판단의 근거다.
   세 가지를 모두 뽑는다. 읽기 전용 SELECT만 쓴다.
   ```bash
   # source 분포 (search/direct/internal/referral) — 주간 방문 수와 순방문자 수.
   sqlite3 backend/data/baduk.db "SELECT source, COUNT(*) AS hits, COUNT(DISTINCT visitor_hash) AS visitors FROM visit_hits WHERE created_at >= datetime('now', '-7 days') GROUP BY source ORDER BY hits DESC;"
   # 상위 referrer_host — 검색엔진·외부 링크 출처.
   sqlite3 backend/data/baduk.db "SELECT referrer_host, COUNT(*) FROM visit_hits WHERE created_at >= datetime('now', '-7 days') AND referrer_host IS NOT NULL AND source != 'internal' GROUP BY referrer_host ORDER BY 2 DESC LIMIT 10;"
   # 상위 랜딩 경로군 — 첫 두 세그먼트로 묶어 글로서리·FAQ·프로기보 등 섹션 단위로 본다.
   sqlite3 backend/data/baduk.db "SELECT CASE WHEN instr(substr(path,2),'/')>0 THEN substr(path,1,instr(substr(path,2),'/')) ELSE path END AS section, COUNT(*) AS hits, COUNT(DISTINCT visitor_hash) AS visitors FROM visit_hits WHERE created_at >= datetime('now', '-7 days') GROUP BY section ORDER BY hits DESC LIMIT 10;"
   # 전주 대비: 위 첫 쿼리의 WHERE를 created_at >= datetime('now','-14 days') AND created_at < datetime('now','-7 days')로 바꿔 한 번 더.
   ```
   주의. `visit_hits.created_at`은 UTC naive이고, 봇은 수집 단계에서 이미 걸러져 있다.
   `source='internal'`은 사이트 내부 이동이므로 신규 유입 판단에서 분리해 읽는다.

   추가 운영 카운트:
   ```bash
   # 보류 승인 — '## 대기 중'~'## 처리 완료' 구간의 실제 AP 항목(### AP-)만 센다.
   # (전체 '- ' 글머리를 세면 '처리 완료' 섹션 설명 줄까지 잡혀 오집계됨.)
   awk '/## 대기 중/{f=1;next} /## 처리 완료/{f=0} f && /^### AP-/{c++} END{print c+0}' docs/ops/state/pending-approvals.md  # 보류 승인
   ls web/content/glossary/*.md 2>/dev/null | grep -v gitkeep | wc -l  # 글로서리 게시 수
   ls web/content/faq/*.md 2>/dev/null | grep -v gitkeep | wc -l  # FAQ 게시 수
   ```

3. **리포트 작성** — `docs/ops/state/reports/<YYYY-Www>.md` 새 파일. 약 500자 한국어
   마크다운. frontmatter:
   ```
   ---
   week: <YYYY-Www>
   generated_at: <YYYY-MM-DD HH:MM>
   ---
   ```
   본문 구성:
   - **사용량** — 이번 주 게임 수 / 전체 누적, 전주 대비 증감(±N, ±%).
   - **세션** — 이번 주 신규 세션 / 전체 누적. (재방문 정밀 추정은 불가 — 단순 카운트.)
   - **유입** — source 분포(hits·순방문자, 전주 대비 증감), 상위 referrer_host 3개,
     상위 랜딩 경로군 3개. 검색 유입이 어느 섹션으로 떨어지는지 한 줄로 짚는다.
   - **분포** — 인기 보드 크기(9·13·19), 핸디캡 분포 상위.
   - **콘텐츠** — 글로서리·FAQ 게시 수. 신규 1개 있으면 강조.
   - **운영** — 보류 승인 건, incidents 최근.
   - 결산: 한 줄. 사실만, 의견 없음.
   
   **숫자는 명령 출력에서 정확히 인용한다.** 환각 금지. 모호하면 "(데이터 부족)"으로
   적는다.

4. **보고** — Telegram으로 직접 보내지 않는다. 리포트 생성 결과를 상태 파일에 기록한다.

   ```bash
   ops/report-job-status.sh analytics-weekly ok "<주차> 리포트 생성 — 방문 <N>건"
   ```

   일요일 09:00 다이제스트가 `자동화` 행에 한 줄로 싣고 파일 경로를 푸터로 남긴다.

5. **로그** — `docs/ops/state/log/YYYY-MM-DD.md`에 한 줄.

## 끝낼 때

한 일을 2~3줄로 요약하고 종료. 이 세션은 1회성. 다음 실행은 다음 일요일 launchd.

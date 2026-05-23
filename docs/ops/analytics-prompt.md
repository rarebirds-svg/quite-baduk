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

   추가 운영 카운트:
   ```bash
   grep -c '^- ' docs/ops/state/pending-approvals.md  # 보류 승인
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
   - **분포** — 인기 보드 크기(9·13·19), 핸디캡 분포 상위.
   - **콘텐츠** — 글로서리·FAQ 게시 수. 신규 1개 있으면 강조.
   - **운영** — 보류 승인 건, incidents 최근.
   - 결산: 한 줄. 사실만, 의견 없음.
   
   **숫자는 명령 출력에서 정확히 인용한다.** 환각 금지. 모호하면 "(데이터 부족)"으로
   적는다.

4. **Telegram 푸시** — `docs/ops/runbooks/telegram-protocol.md` 알림 형식.
   본문 100자 요약 + 보관 경로. `reply` 도구 없으면 curl Bot API 폴백
   (`ops/ops.env`의 TELEGRAM_CHAT_ID).

5. **로그** — `docs/ops/state/log/YYYY-MM-DD.md`에 한 줄.

## 끝낼 때

한 일을 2~3줄로 요약하고 종료. 이 세션은 1회성. 다음 실행은 다음 일요일 launchd.

# Agentic Ops 분석·리포트 (하위 프로젝트 4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매주 일요일 09:00 헤드리스 Claude가 prod 통계를 요약해 `docs/ops/state/reports/`에 누적 + Telegram 푸시. 오케스트레이터 일일 요약에 한 줄 통합.

**Architecture:** 새 launchd 작업 `com.inkbaduk.analytics-weekly`가 헤드리스 `claude -p`를 깨워 `docs/ops/analytics-prompt.md` 지시문 실행. 데이터 소스는 공개 `/api/stats` + DB 읽기 전용(`backend/data/baduk.db` SQLite). LLM이 한국어 요약 작성 → `docs/ops/state/reports/<YYYY-Www>.md` 저장 → Telegram 푸시. 0~3c launchd 패턴과 동일.

**Tech Stack:** macOS launchd, 헤드리스 Claude Code, curl + sqlite3, Markdown.

**브랜치:** 모든 작업은 `feat/agentic-ops-analytics`에서. spec 커밋 `e6d3ec2`가 올라가 있음. base는 `feat/agentic-ops-sre`(0~3c 머지 후).

**전제:** sub-project 0~3c 머지된 상태. prod `/api/stats` 가동. `claude` `/opt/homebrew/bin/claude`.

**경로 상수:** 리포 루트 `/Users/daegong/projects/baduk`.

**앱 코드 미수정**: ops 파일만 추가, prod 무영향.

---

### Task 1: 리포트 디렉터리 + analytics-prompt.md

헤드리스 세션이 실행할 지시문과 리포트 저장 경로.

**Files:**
- Create: `docs/ops/state/reports/.gitkeep`
- Create: `docs/ops/analytics-prompt.md`

- [ ] **Step 1: 디렉터리·gitkeep 생성**

```bash
mkdir -p /Users/daegong/projects/baduk/docs/ops/state/reports
touch /Users/daegong/projects/baduk/docs/ops/state/reports/.gitkeep
```

- [ ] **Step 2: `docs/ops/analytics-prompt.md` 작성** — 다음 그대로:

```markdown
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
   sqlite3 backend/data/baduk.db "SELECT COUNT(*) FROM games WHERE created_at >= date('now', '-7 days');"
   sqlite3 backend/data/baduk.db 'SELECT COUNT(*) FROM sessions;'
   sqlite3 backend/data/baduk.db "SELECT COUNT(*) FROM sessions WHERE created_at >= date('now', '-7 days');"
   sqlite3 backend/data/baduk.db 'SELECT board_size, COUNT(*) FROM games GROUP BY board_size ORDER BY 2 DESC;'
   sqlite3 backend/data/baduk.db 'SELECT handicap, COUNT(*) FROM games GROUP BY handicap ORDER BY 2 DESC LIMIT 5;'
   sqlite3 backend/data/baduk.db "SELECT COUNT(*) FROM games WHERE created_at >= date('now', '-14 days') AND created_at < date('now', '-7 days');"
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
```

- [ ] **Step 3: 확인**

```bash
find docs/ops/state/reports docs/ops/analytics-prompt.md -type f | sort
```
Expected: 2개 파일.

- [ ] **Step 4: 커밋**

```bash
git add docs/ops/state/reports docs/ops/analytics-prompt.md
git commit -m "feat(ops): 주간 분석 리포트 지시문 + reports 디렉터리"
```

---

### Task 2: `run-analytics-weekly.sh` + launchd

**Files:**
- Create: `ops/run-analytics-weekly.sh`
- Create: `ops/launchd/com.inkbaduk.analytics-weekly.plist`

- [ ] **Step 1: `ops/run-analytics-weekly.sh`**:

```bash
#!/usr/bin/env bash
# launchd가 매주 일요일 09:00 호출 — 주간 분석 리포트 헤드리스 Claude를 1회 실행.
set -euo pipefail
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT"

[ -f ops/ops.env ] && { set -a; . ops/ops.env; set +a; }

mkdir -p docs/ops/state/log docs/ops/state/reports
RUNLOG="docs/ops/state/log/analytics-weekly-runs.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] analytics-weekly 시작" >> "$RUNLOG"

/opt/homebrew/bin/claude -p "$(cat docs/ops/analytics-prompt.md)" \
  --dangerously-skip-permissions \
  --channels plugin:telegram@claude-plugins-official \
  >> "$RUNLOG" 2>&1 || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] analytics-weekly 종료" >> "$RUNLOG"
```

- [ ] **Step 2: 실행 권한**

`chmod +x /Users/daegong/projects/baduk/ops/run-analytics-weekly.sh`

- [ ] **Step 3: `ops/launchd/com.inkbaduk.analytics-weekly.plist`**:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- 매주 일요일 09:00 주간 분석 리포트를 생성하는 launchd 작업. -->
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.inkbaduk.analytics-weekly</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/daegong/projects/baduk/ops/run-analytics-weekly.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>0</integer>
    <key>Hour</key><integer>9</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/analytics-weekly.out.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/analytics-weekly.err.log</string>
</dict>
</plist>
```

(macOS launchd `Weekday=0` 일요일.)

- [ ] **Step 4: launchd 등록**

```bash
cp /Users/daegong/projects/baduk/ops/launchd/com.inkbaduk.analytics-weekly.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.inkbaduk.analytics-weekly.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.inkbaduk.analytics-weekly.plist
launchctl list | grep com.inkbaduk.analytics-weekly
```
Expected: 등록 확인.

- [ ] **Step 5: 검사**

```bash
bash -n /Users/daegong/projects/baduk/ops/run-analytics-weekly.sh && echo "shell OK"
plutil -lint /Users/daegong/projects/baduk/ops/launchd/com.inkbaduk.analytics-weekly.plist
xmllint --noout /Users/daegong/projects/baduk/ops/launchd/com.inkbaduk.analytics-weekly.plist && echo "xml OK"
```
Expected: 셋 다 OK.

- [ ] **Step 6: 커밋**

```bash
git add ops/run-analytics-weekly.sh ops/launchd/com.inkbaduk.analytics-weekly.plist
git commit -m "feat(ops): analytics-weekly launchd (일요일 09:00)"
```

이 태스크에서 `launchctl start` 트리거 금지. 실제 실행 검증은 Task 4.

---

### Task 3: 오케스트레이터 일일 요약에 분석 리포트 한 줄

**Files:**
- Modify: `docs/ops/orchestrator-prompt.md`

- [ ] **Step 1: 보고 섹션 수정**

`docs/ops/orchestrator-prompt.md`에서 다음 블록을 찾는다:
```
4. **보고** — `docs/ops/runbooks/telegram-protocol.md` 형식으로 Telegram에 보낸다.
   - prod 이상이 있으면 경보를 보낸다.
   - 이상이 없어도 매 실행 시 상태 요약을 1건 보낸다 — 헬스 OK 여부,
     `state/pending-approvals.md` "대기 중" 건수, `state/log/content-ingest-runs.log`에서
     읽은 가장 최근 CWI ingest 결과(0건이면 "신규 0")를 포함한다. 하루 2회라 과하지 않다.
```

다음으로 교체:
```
4. **보고** — `docs/ops/runbooks/telegram-protocol.md` 형식으로 Telegram에 보낸다.
   - prod 이상이 있으면 경보를 보낸다.
   - 이상이 없어도 매 실행 시 상태 요약을 1건 보낸다 — 헬스 OK 여부,
     `state/pending-approvals.md` "대기 중" 건수, `state/log/content-ingest-runs.log`에서
     읽은 가장 최근 CWI ingest 결과(0건이면 "신규 0"), `state/reports/`의 가장 최근
     주간 리포트 파일명(예: "최근 분석: 2026-W21")을 포함한다. 하루 2회라 과하지 않다.
```

찾는 블록이 정확히 일치하지 않으면(공백·줄바꿈) 의미적으로 동일하게 — 즉 "최근 분석 리포트 파일명" 한 줄을 보고 항목에 추가한다.

- [ ] **Step 2: 커밋**

```bash
git add docs/ops/orchestrator-prompt.md
git commit -m "feat(ops): 오케스트레이터 일일 요약에 최근 분석 리포트 한 줄"
```

---

### Task 4: 검증 + 통합 + 대시보드

검증 기준 3가지 실증.

**Files:**
- Modify: `docs/ops/state/dashboard.md`
- Modify: `docs/ops/state/log/2026-05-23.md`

- [ ] **Step 1: launchd 등록 + 수동 트리거**

```bash
launchctl list | grep com.inkbaduk.analytics-weekly
launchctl start com.inkbaduk.analytics-weekly
echo "헤드리스 Claude 실행 중 — 최대 5분 대기"
sleep 180
tail -40 docs/ops/state/log/analytics-weekly-runs.log
```

5분 후에도 로그가 비면 추가 60초 대기 (최대 7분). LLM이 stats 수집 + 요약 + Telegram까지 하는 데 시간 걸린다.

- [ ] **Step 2: 검증 기준 #1 — 리포트 파일 생성 + Telegram**

```bash
WEEK=$(date '+%G-W%V')
echo "현재 ISO 주차: $WEEK"
ls -la docs/ops/state/reports/
cat "docs/ops/state/reports/$WEEK.md" 2>/dev/null | head -30 || echo "리포트 파일 미생성"
```
Expected: `<현재 주차>.md` 파일 존재 + frontmatter + 본문. Telegram 발송 여부는 launchd 로그에 표시(HTTP 200 또는 fallback curl 출력).

- [ ] **Step 3: 검증 기준 #2 — 통계 정확성 스폿체크**

리포트 본문의 숫자 몇 개를 실제 DB와 대조:
```bash
echo "--- 리포트의 게임 수 vs 실제 ---"
grep -E '게임 수|games' "docs/ops/state/reports/$WEEK.md" | head -3
sqlite3 backend/data/baduk.db 'SELECT COUNT(*) FROM games;'
```
LLM 환각 없이 정확한 숫자 인용했는지 확인. 어긋나면 DONE_WITH_CONCERNS — 프롬프트 보강 필요.

- [ ] **Step 4: 검증 기준 #3 — 오케스트레이터 한 줄**

```bash
grep -A1 'state/reports' docs/ops/orchestrator-prompt.md
```
Expected: "최근 분석 리포트" 지시 라인 존재.

- [ ] **Step 5: prod 무손상**

```bash
curl -fs http://localhost:8000/api/health && echo " backend-OK"
curl -fs http://localhost:3000 >/dev/null && echo "web-OK"
```

- [ ] **Step 6: 대시보드 + 로그 갱신**

`docs/ops/state/dashboard.md`의 `## 콘텐츠 인덱스` 섹션 다음에 (없으면 `## 최근 장애` 앞) 추가:
```
## 분석

| 항목 | 값 |
|---|---|
| 최근 주간 리포트 | <현재 주차>.md |
| 누적 리포트 수 | <count> |
```
`<현재 주차>` = Task 4 Step 2의 결과. `<count>` = `ls docs/ops/state/reports/*.md | wc -l`.

`docs/ops/state/log/2026-05-23.md`에 시간순 추가:
```
## <현재시각> — 분석·리포트(sub-project 4) 구축 완료
- 검증 기준 3/3 통과: ① 리포트 파일 생성 + Telegram 발송 ② 통계 정확성 스폿체크 ③ 오케스트레이터 한 줄
- 첫 주간 리포트: docs/ops/state/reports/<주차>.md
```

- [ ] **Step 7: 커밋**

```bash
git add docs/ops/state
git commit -m "feat(ops): 분석·리포트 구축 완료 — 검증 기준 3/3 통과"
```

- [ ] **Step 8: 최종 보고**

---

## 검증 기준 (spec)

1. analytics-weekly launchd 등록 + 트리거로 `docs/ops/state/reports/<주차>.md` 생성 + Telegram 발송. → Task 2, 4
2. 리포트의 숫자가 실제 DB 통계와 일치(LLM 환각 없음). → Task 1(프롬프트가 강제), Task 4(스폿체크)
3. 오케스트레이터 일일 요약에 "최근 분석" 한 줄. → Task 3, 4

# 승인 대기 큐

🟡 액션 제안이 여기 쌓인다. 형식은 `runbooks/telegram-protocol.md` 참조.
처리 완료 항목은 큐에서 제거하고 `state/log/`로 옮긴다.

## 대기 중

### AP-20260525-01
- 액션: 초안 게시 — `chuk` (glossary)
- 근거: 콘텐츠 초안 사이클이 글로서리 시드의 미작성 슬러그 중 알파벳 순 첫 번째(`chuk`)를 생성하고 korean-copy-qa 점검을 통과했다. 라이브 게시는 🟡.
- 영향: `web/content/glossary/chuk.md` 신규 파일 1개 + main 커밋 1개.
- 실행 절차:
  ```
  mv docs/ops/content/drafts/chuk.md web/content/glossary/chuk.md
  git add web/content/glossary/chuk.md docs/ops/content/drafts/chuk.md
  git commit -m "content(glossary): chuk 게시"
  ```
- 상태: 대기

### AP-20260525-02
- 액션: PR #30 `feat(db): last_seen_at 매 요청 UPDATE를 60s 디바운스 캐시로 대체` 머지
  (main 변경 → 🟡).
- 근거: `~/Library/Logs/baduk-api.err`에 `sqlite3.OperationalError: database is locked`
  누적 2262건, 마지막 발생 2026-05-25 17:56. 원인은 `app/deps.py:51`이 매 요청마다
  `sessions.last_seen_at`을 동기 UPDATE하는 핫패스. 본 PR이 정확히 그 경로의 60s
  디바운스 캐시화이며 CI(backend/frontend/e2e) 전부 SUCCESS, mergeable MERGEABLE,
  mergeStateStatus CLEAN.
- 영향: sessions 핫패스가 매 요청 SQLite write → 60s 1회 write로 감소. 머지는 main
  변경만이며 배포(launchd 재시작)는 별도. 로그 노이즈와 잠재적 응답 지연 감소.
- 실행 절차:
  ```
  /opt/homebrew/bin/gh pr merge 30 --squash --delete-branch
  ```
  머지 후 `state/log/2026-05-25.md`에 결과 기록, 본 항목을 큐에서 제거.
- 상태: 대기

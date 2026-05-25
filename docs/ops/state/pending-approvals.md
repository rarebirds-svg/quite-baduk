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


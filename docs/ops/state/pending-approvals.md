# 승인 대기 큐

🟡 액션 제안이 여기 쌓인다. 형식은 `runbooks/telegram-protocol.md` 참조.
처리 완료 항목은 큐에서 제거하고 `state/log/`로 옮긴다.

## 대기 중

### AP-20260523-03
- 액션: 초안 게시 — `bik` (glossary)
- 근거: 콘텐츠 초안 사이클(주 1회)에서 작성·QA 완료. 라이브 게시는 🟡로 사람 승인 필요.
- 영향: `web/content/glossary/bik.md`에 새 파일 추가 + git commit. 사용자에게 신규 글로서리 페이지(/glossary/bik) 노출.
- 실행 절차: `mv docs/ops/content/drafts/bik.md web/content/glossary/bik.md && git add web/content/glossary/bik.md && git commit -m "content(glossary): bik 게시"`
- 상태: 대기

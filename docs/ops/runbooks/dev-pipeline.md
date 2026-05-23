# 러닝북: 개발 파이프라인

GitHub 이슈를 크기별로 처리하는 절차다.

## bug · small 이슈 → 자율 경로

전용 worktree(`.worktrees/dev-cycle`)에서.

1. `git -C .worktrees/dev-cycle fetch origin`, `origin/main` 기준으로 `fix/issue-<N>` 브랜치 생성.
2. 수정한다.
   - 로직 버그 — TDD: 버그를 재현하는 실패 테스트 작성 → 수정 → 통과 확인.
   - 오타·주석·문구 등 비로직 수정 — 테스트 추가 없이 수정하고 기존 테스트가 깨지지
     않는지 확인.
3. 커밋한다. 푸시·PR 생성은 자율 세션에서 시도하지 마라 — `settings.json`의 deny
   규칙이 헤드리스에서 `git push`를 차단한다(`[[dev-cycle-push-blocked]]`). 대신
   이슈에 다음 핸드오프 코멘트를 남기고 에스컬레이션 처리한다.
   - 작성한 브랜치명·커밋 SHA.
   - 사람이 1회 실행할 명령:
     `cd .worktrees/dev-cycle && git push -u origin fix/issue-<N> && gh pr create --base main --head fix/issue-<N> --title "<제목>" --body "Closes #<N>"`.
4. 확신이 안 서거나 테스트가 통과하지 않으면 커밋도 만들지 말고 이슈에 막힌 지점만
   코멘트로 남기고 에스컬레이션한다.

## feature 이슈 → 온디맨드 경로

사용자가 "이슈 #N 진행"으로 트리거한다. cron 자동화하지 않는다.

1. `superpowers:brainstorming` — 사용자와 설계.
2. `superpowers:writing-plans` — 구현 계획.
3. `superpowers:subagent-driven-development` — 태스크별 구현·리뷰.
4. PR 생성.

PR 머지는 어느 경로든 🟡 — 사람이 한다.

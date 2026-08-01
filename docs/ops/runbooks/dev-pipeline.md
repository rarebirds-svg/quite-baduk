# 러닝북: 개발 파이프라인

GitHub 이슈를 크기별로 처리하는 절차다.

## bug · small 이슈 → 자율 경로

전용 worktree(`.worktrees/dev-cycle`)에서.

1. 워크트리가 없으면 먼저 만든다 —
   `[ -d .worktrees/dev-cycle ] || git worktree add --detach .worktrees/dev-cycle origin/main`.
   그다음 `git -C .worktrees/dev-cycle fetch origin`, `origin/main` 기준으로 `fix/issue-<N>` 브랜치 생성.
2. 수정한다.
   - 로직 버그 — TDD: 버그를 재현하는 실패 테스트 작성 → 수정 → 통과 확인.
   - 오타·주석·문구 등 비로직 수정 — 테스트 추가 없이 수정하고 기존 테스트가 깨지지
     않는지 확인.
3. 커밋하고, **push·PR 생성까지 자율로 끝낸다**. feature 패턴(`fix/*`·`feat/*`·
   `chore/*`·`docs/*`·`test/*`) 브랜치 push와 PR 생성은 🟢다 — `settings.json`
   allow 목록에 명시돼 있고 `autonomy-policy.md`가 같은 등급을 준다.

   ```sh
   cd .worktrees/dev-cycle
   git push -u origin fix/issue-<N>
   gh pr create --base main --head fix/issue-<N> --title "<제목>" --body "Closes #<N>"
   ```

   그다음 이슈에 브랜치명·커밋 SHA·PR 링크를 코멘트로 남기고 `in-progress`를 뗀다.
   **머지만 🟡** — 사람이 한다.

   > push하지 않고 로컬에만 두지 마라. 그러면 사람이 리뷰할 대상 자체가 없어 픽스가
   > 무기한 지연된다 — 2026-06-01 `fix/issue-39`가 실제로 그렇게 누락됐다.
4. 확신이 안 서거나 테스트가 통과하지 않으면 커밋도 만들지 말고 이슈에 막힌 지점만
   코멘트로 남기고 에스컬레이션한다.

## feature 이슈 → 온디맨드 경로

사용자가 "이슈 #N 진행"으로 트리거한다. cron 자동화하지 않는다.

1. `superpowers:brainstorming` — 사용자와 설계.
2. `superpowers:writing-plans` — 구현 계획.
3. `superpowers:subagent-driven-development` — 태스크별 구현·리뷰.
4. PR 생성.

PR 머지는 어느 경로든 🟡 — 사람이 한다.

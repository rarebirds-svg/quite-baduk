# 러닝북: 배포 (staging → prod 승급)

- 등급: 🟡 승인 — prod를 바꾸므로 Telegram 승인 후에만 3단계를 실행한다.
- 전제: 승급할 변경이 feature 브랜치에 커밋돼 있다.

## 1. staging 검증

feature 브랜치를 staging worktree에 체크아웃하고 빌드+테스트한다.

```bash
BR=<feature-branch>
git -C .worktrees/staging fetch origin
git -C .worktrees/staging checkout "$BR"
( cd .worktrees/staging/backend && source .venv311/bin/activate \
    && pip install -e ".[dev]" -q && alembic upgrade head && pytest -q )
( cd .worktrees/staging/web && npm run build && npm test -- --run )
```
판정: pytest·npm test·npm build가 모두 통과해야 다음 단계로. 하나라도 실패하면 중단하고
실패를 보고한다 — prod는 건드리지 않는다.

## 2. 제안 (🟡)

`runbooks/telegram-protocol.md`의 승인 절차대로 `state/pending-approvals.md`에 항목을
추가하고 Telegram으로 제안한다. 항목의 "실행 절차"에는 아래 3단계를 적는다 —
브랜치명과, 승급 직전 기록할 `main` SHA 자리를 포함한다.

## 3. 승급 (승인 후에만)

```bash
PREV=$(git rev-parse main)            # 롤백 대상 — 반드시 먼저 기록
echo "롤백 SHA: $PREV"
git checkout main && git merge --no-ff <feature-branch>
( cd backend && source .venv311/bin/activate \
    && pip install -e ".[dev]" -q && alembic upgrade head )
( cd web && npm run build )
ops/stack.sh restart prod
```
주의: prod web은 `npm start`가 `.next`를 서빙하므로 `npm run build` 없이는 새 코드가
반영되지 않는다. backend 의존성이 안 바뀌었으면 `pip install`은 건너뛰어도 된다.

## 4. 사후 확인 + 롤백

```bash
curl -fs --max-time 10 http://localhost:8000/api/health && echo " prod-backend OK"
curl -fs --max-time 10 http://localhost:3000 >/dev/null && echo "prod-web OK"
```
판정: 둘 다 OK면 승급 성공 — `state/log/`에 기록하고 Telegram으로 결과 회신.

헬스체크가 실패하면 **롤백**한다(3단계에서 기록한 `$PREV` 사용):

```bash
git checkout main && git reset --hard <PREV-SHA>
( cd web && npm run build )
ops/stack.sh restart prod
curl -fs --max-time 10 http://localhost:8000/api/health && echo " 롤백 후 OK"
```
롤백 후에도 실패하면 `incident.md`로 전환하고 Telegram 긴급 경보.

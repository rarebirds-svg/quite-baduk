# 러닝북: PR 감시

- 주기: 매일 06:30·12:30·18:30·23:30 (오케스트레이터)
- 등급: 🟢 자율 (보고까지. PR 수정은 dev 작업.)
- 목적: 열린 PR의 CI·머지 상태를 점검하고 정체·실패 PR을 보고한다.

## 절차

### 1. 열린 PR 수집

```bash
gh pr list --state open --json number,title,createdAt,mergeable,statusCheckRollup
```

### 2. 판정

각 PR을 다음으로 분류한다.
- CI 실패 — `statusCheckRollup`에 실패 체크가 있음.
- 충돌 — `mergeable`이 `CONFLICTING`.
- 정체 — `createdAt`이 7일 이상 지났는데 열려 있음.
- 정상 — 위에 해당 없음.

## 결과 처리

CI 실패·충돌·정체 PR의 번호와 사유를 `state/log/YYYY-MM-DD.md`에 기록하고,
일일 요약에 "주의 PR N건"으로 포함한다. 정상 PR만 있으면 "열린 PR 모두 정상".
실제 수정(rebase·CI 고치기)은 dev 작업이라 백로그 항목화하거나 온디맨드로 처리한다.

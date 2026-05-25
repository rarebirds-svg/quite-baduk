# 러닝북: 버그 스캔

- 주기: 매일 06:30·12:30·18:30·23:30 (오케스트레이터)
- 등급: 🟢 자율 (이슈 생성까지. 수정은 dev-cycle/온디맨드.)
- 목적: 로그에서 반복되는 진짜 에러를 찾아 GitHub `bug` 이슈로 올린다.

## 절차

### 1. 로그 수집

```bash
tail -200 ~/Library/Logs/baduk-api.err 2>/dev/null
tail -100 docs/ops/state/incidents.md
```

### 2. 후보 선별

수집한 로그에서 다음을 만족하는 에러만 후보로 삼는다.
- 스택 트레이스나 명확한 예외 메시지가 있다.
- 1회성이 아니라 반복된다(같은 에러가 2회 이상).
- 일시적 인프라 잡음(네트워크 타임아웃 등)이 아니다.

### 3. 중복 차단

```bash
gh issue list --state open --label bug --json title --jq '.[].title'
```
후보 에러가 이미 열린 `bug` 이슈로 있으면 건너뛴다.

### 4. 이슈 생성

새 후보만 이슈로 만든다.
```bash
gh issue create --label bug --title "<한 줄 요약>" \
  --body "스캔 출처: <로그 파일>\n\n<에러 발췌>\n\n자동 탐지(bug-scan)."
```

## 결과 처리

생성한 이슈 수를 `state/log/YYYY-MM-DD.md`에 기록한다. 0건이면 "신규 버그 없음"으로
기록한다. Telegram 보고는 오케스트레이터가 실행 요약으로 처리한다.

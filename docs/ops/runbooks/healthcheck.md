# 러닝북: 헬스체크

- 주기: 매일 06:30·12:30·18:30·23:30 (오케스트레이터)
- 등급: 🟢 자율
- 목적: prod·staging 스택 정상 여부를 확인하고, 이상 시에만 Telegram 경보.

## 절차

### 1. prod 헬스

```bash
curl -fs --max-time 10 http://localhost:8000/api/health && echo " prod-backend OK"
curl -fs --max-time 10 http://localhost:3000 >/dev/null && echo "prod-web OK"
launchctl list | grep -E 'com\.baduk\.(api|web)'
```
판정: 두 curl이 성공하고 `com.baduk.api`·`com.baduk.web`가 launchctl 목록에 있으면 정상.
launchctl 행의 첫 컬럼이 PID(숫자)면 가동, `-`면 중단.

**중요**: `/api/health` 응답의 `katago_alive` 필드는 **정보용**이지 경보 신호가 아니다.
KataGo는 첫 AI 응수 요청 시 lazy spawn되므로 backend 재시작 직후나 한동안 AI 호출이
없으면 `katago_alive:false`가 정상이다. 이 필드 단독으로 incident를 만들거나 prod 재시작을
제안하지 마라(false alarm). 진짜 KataGo 실패는 "사용자가 응수 요청했는데 일정 시간 내
미반환" 등 활동-연관 신호로만 판정한다.

### 2. staging 헬스

```bash
ops/stack.sh ps staging
```
판정: staging은 상시 가동이 필수가 아니다. `중단됨`이면 `중단`으로만 기록(경보 아님).

### 3. 디스크 여유

```bash
df -h / | tail -1 | awk '{print $5}'
```
판정: 사용률 90% 이상이면 경보.

### 4. launchd plist drift

```bash
ops/sync-launchd.sh --check
```
판정: exit 0 + 출력 없음이면 정상. 비0이면 `~/Library/LaunchAgents/`의 plist가
repo `ops/launchd/`와 다름 → drift incident로 기록.

### 5. sleep/wake 진단 (필요 시)

watchdog가 잡 stale을 감지한 경우 또는 launchd trigger 누락이 의심될 때만 실행한다.

```bash
pmset -g | grep -E '^\s+(sleep|standby|hibernatemode|womp)'
pmset -g sched
log show --predicate 'subsystem == "com.apple.xpc.launchd" AND eventMessage CONTAINS "com.inkbaduk"' \
  --last 7d | tail -50
```
판정: `sleep` 값이 0이 아니거나, 7일 log에서 예상되는 trigger 시각의 entry가
빠져 있으면 `state/incidents.md`에 sleep-related로 기록하고 사람에게 보고.

## 결과 처리

1. 결과를 `state/log/YYYY-MM-DD.md`에 추가한다 (시각·항목별 OK/실패).
2. `state/dashboard.md`의 스택 상태 표를 갱신한다.
3. **prod 이상이 하나라도 있으면** `state/incidents.md`에 항목을 추가한다.
4. Telegram 보고(경보·정상 요약)는 오케스트레이터가 실행 요약으로 처리한다.

4·5번에서 비정상이면 watchdog incident와 별도로 기록한다 (id 접두: `DRIFT-` / `SLEEP-`).

## 범위 메모

백업 신선도·공개 도메인(cloudflared) 점검은 sub-project 1(SRE)의 백업·배포 러닝북에서
다룬다. 이 러닝북은 로컬 prod·staging 가용성에 집중한다.

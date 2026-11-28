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

### 6. Claude 인증

```bash
ops/check-claude-auth.sh
```
출력 한 줄 예시.
- `ok: Claude 인증 D-29 (만료 10-04 08:47)` — 정상.
- `warn: Claude 인증 D-2 (만료 09-06 08:47)` — 만료까지 D-3 이내.
- `fail: Claude 인증 만료 (09-04 04:12) — claude /login 필요` — 만료됨.
- `warn: Claude 인증 확인 불가 (자격증명 명령 실패)` — 판정 불가 (그 밖에 `자격증명 응답 없음` · `JSON 파싱 실패` · `만료 필드 없음`).

판정: 종료코드 0(ok) · 2(warn) · 1(fail). `fail`이면 장애 기록.

장기 토큰 모드(아래 설정 후)에서는 출력이 이렇게 바뀐다.
- `ok: Claude 장기 토큰 D-355 (만료 추정 10-28 21:30)` — 정상.
- `warn: Claude 장기 토큰 D-12 (만료 추정 ...) — claude setup-token 재발급 권장` — 만료 14일 이내.
- `fail: Claude 장기 토큰 만료 추정 (...) — claude setup-token 재발급 필요` — 만료.
- `warn: Claude 장기 토큰 파일 권한 644 — chmod 600 필요` — 파일 권한이 넓음.

복구(키체인 /login 모드): 터미널에서 `claude` → `/login` → `/exit` 실행. 이후 `claude auth status`로 `loggedIn: true` 확인.
재로그인 후 refresh 토큰은 약 30일 유효하며, 만료 시 헤드리스 잡은 `session-retry.sh`가 보류 마커를 남기고
watchdog(`ops/check-auth-recovery.sh`)이 인증 회복을 감지한 뒤 1회 자동 재트리거한다.

#### 장기 토큰 설정 (권장 — 30일마다 반복되던 만료 제거)

`/login` 토큰은 약 30일마다 만료돼 7/28·9/4·10/3·11/2 네 차례 헤드리스 잡 전체가 멈췄다.
`claude setup-token`은 1년 유효 토큰을 발급한다(Pro·Max·Team·Enterprise 구독 필요, 모델 호출 전용 —
claude.ai 커넥터·Remote Control에는 못 쓴다. 로컬 MCP·플러그인은 동작).
`ops/claude-headless.sh`는 아래 파일이 있으면 그 값을 `CLAUDE_CODE_OAUTH_TOKEN`으로 넘기고,
`ops/check-claude-auth.sh`는 파일 저장 시각 + 365일로 만료를 추정해 14일 전부터 경고한다.

```bash
claude setup-token                              # 브라우저 인증 후 토큰이 터미널에 출력된다(저장되지 않음)
mkdir -p ~/.config/inkbaduk && chmod 700 ~/.config/inkbaduk
pbpaste > ~/.config/inkbaduk/claude-oauth-token # 출력된 토큰을 복사한 뒤 실행
chmod 600 ~/.config/inkbaduk/claude-oauth-token
bash ops/check-claude-auth.sh                   # ok: Claude 장기 토큰 D-364 ... 확인
```

주의
- 파일은 토큰 원문(bearer 자격증명)이다. 권한 600 유지, 리포·백업 경로에 두지 않는다.
- 재발급 시에는 같은 파일을 덮어쓴다 — 저장 시각이 곧 만료 추정 기준이다.
- 토큰을 쓰기로 했으면 러너가 `ANTHROPIC_API_KEY`·`ANTHROPIC_AUTH_TOKEN`을 비운다(공식 우선순위상 이 둘이 토큰을 이긴다).
- 같은 Mac의 다른 프로젝트(popory) 잡은 이 러너를 쓰지 않으므로, 그쪽 러너에도 같은 환경변수 주입이 필요하다.
- 첫 적용 직후 잡 하나를 수동 트리거해(`launchctl kickstart gui/$(id -u)/com.inkbaduk.dev-cycle`) 인증 성공을 확인한다.
  실패하면 파일을 지우면 즉시 키체인 `/login` 경로로 돌아간다.

## 결과 처리

1. 결과를 `state/log/YYYY-MM-DD.md`에 추가한다 (시각·항목별 OK/실패).
2. `state/dashboard.md`의 스택 상태 표를 갱신한다.
3. **prod 이상이 하나라도 있으면** `state/incidents.md`에 항목을 추가한다.
4. Telegram 보고(경보·정상 요약)는 오케스트레이터가 실행 요약으로 처리한다.

4·5번에서 비정상이면 watchdog incident와 별도로 기록한다 (id 접두: `DRIFT-` / `SLEEP-`).

## 범위 메모

백업 신선도·공개 도메인(cloudflared) 점검은 sub-project 1(SRE)의 백업·배포 러닝북에서
다룬다. 이 러닝북은 로컬 prod·staging 가용성에 집중한다.

# 러닝북: 장애 대응

- 등급: 🟢 안전 복구 한정 (`autonomy-policy.md`의 화이트리스트). 그 외 에스컬레이션.
- 입력: healthcheck가 보고한 실패 항목 (예: prod backend 무응답, staging backend 다운).
- 트리거: 오케스트레이터가 healthcheck 실패를 잡으면 이 러닝북으로 연결한다.

## 절차

### 1. 실패 분류

실패 항목이 `autonomy-policy.md`의 "장애 안전 복구 화이트리스트"에 해당하는가.
- 해당하면 → 2번(안전 복구).
- 해당하지 않으면(DB 손상, 재시작 루프, prod 데이터 디스크 풀, 코드 오류 등) → 4번(에스컬레이션).

### 2. 루프 가드

`state/incidents.md`를 읽는다. 직전 실행에서 같은 대상을 이미 복구한 기록이 있으면
재시도하지 않고 4번(에스컬레이션)으로 간다.

### 3. 안전 복구 (1회)

화이트리스트의 해당 동작을 1회 수행한다.
- prod 서비스 무응답/다운 → `ops/stack.sh restart prod`
- staging 스택 이상 → `ops/stack.sh down staging` 후 `ops/stack.sh up staging`
- 디스크 압박 → 보존 초과 백업·오래된 `.run/staging-*.log` 삭제

복구 후 재확인:
```bash
sleep 20
curl -fs --max-time 10 http://localhost:8000/api/health && echo " 복구 후 prod OK"
```
(staging 모의 검증 시에는 `http://localhost:8100/api/health`로 확인한다.)

- 재확인 OK → 5번(기록).
- 재확인 실패 → 4번(에스컬레이션).

### 4. 에스컬레이션

자동 수정하지 않는다. `state/incidents.md`에 항목을 추가하고
`runbooks/telegram-protocol.md`의 알림 형식으로 Telegram 긴급 경보를 보낸다.

### 5. 기록

복구 성공·에스컬레이션 모두 `state/incidents.md`와 `state/log/YYYY-MM-DD.md`에
시각·대상·조치·결과를 기록한다. 루프 가드가 다음 실행에서 이 기록을 읽는다.

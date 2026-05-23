# 장애 이력

헬스체크 실패·복구 이력을 시간순으로 기록한다.

## 이력

### 2026-05-23 — prod web :3000 다운 (실 장애)
- 감지: 사용자가 inkbaduk.com 502 Bad gateway 스크린샷 보고. `com.baduk.web` PID `-` / exit 127.
- 진단: `web/node_modules` 비어 있음(23 00:58 변경). `next: command not found`로 launchd가 재시작 포기.
- 조치: AP-20260523-01 승인 후 `cd web && npm install` → `launchctl kickstart -k com.baduk.web`.
- 결과: localhost:3000 200 OK, inkbaduk.com HTTP/2 200. 복구 완료.
- 비고: 화이트리스트 외 동작(`npm install`)이라 자율성 정책대로 승인 게이트 통과. 원인(node_modules 비워짐) 미확정 — sub-project 2 dev-cycle 검증 중 부수효과 추정, 정확한 트리거는 후속 점검.

### 2026-05-23 — staging backend 다운 (검증)
- 감지: :8100 무응답
- 조치: 안전 복구 — staging 스택 재시작
- 결과: 복구 후 :8100 OK
- 비고: sub-project 1 검증 기준 #4 — incident.md 경로 실증.

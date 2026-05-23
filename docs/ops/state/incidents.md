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

### 2026-05-23 18:00 — KataGo "사망" 보고는 false alarm (AP-20260523-02 처리)
- 감지: 18시 오케스트레이터 헬스체크가 `katago_alive:false`를 장애로 raise — AP-02 큐 등록.
- 조치: 사용자 승인 → `launchctl kickstart -k gui/$UID/com.baduk.api` 1회. backend 재기동 성공(PID 72430), 그러나 재확인 시 여전히 `katago_alive:false`. 루프 가드대로 추가 재시도 중지.
- 진단 (코드 확인 — `backend/app/core/katago/adapter.py:106`의 `is_alive`): KataGo는 **첫 AI 응수 요청 시 lazy spawn**된다. backend 재시작 후 AI 호출 전이면 항상 `katago_alive:false`가 정상 — 장애 아님. 12시에 alive였던 것은 그때 활동 중인 게임이 있었기 때문.
- 결과: 사용자 영향 없음 — 접속 중 사용자(game 220) WS 재연결로 끝. 이번 재시작은 불필요했고 ~5초 순단만 발생.
- 후속 (완료): `healthcheck.md` 정정됨 — `/api/health.katago_alive` 필드를 정보용으로 표시, 단독 경보 금지 규칙이 본문에 박혀 있다. 진짜 KataGo 실패는 활동-연관 신호(응수 요청 미반환 등)로만 판정한다.
- 추가 진단성 강화 (작업 트리 적용, 커밋 대기): KataGo subprocess의 stderr를 슬롯별 파일(`KATAGO_STDERR_LOG=~/Library/Logs/baduk-katago-{slot}.err`)로 분리해 실제 거부 사유를 추적 가능하게 만들었고, `_sync_adapter`에 fast→slow path 자동 fallback을 추가해 slot board drift가 자가치유되도록 했다.

# 운영 대시보드

- 갱신: 2026-05-25 21:28

## 스택 상태

| 스택 | 상태 | 마지막 확인 |
|---|---|---|
| prod | 정상 — backend·web 200 OK, db OK, katago lazy (정보), 디스크 5%, plist drift 없음 | 2026-05-25 21:28 |
| staging | 중단 (정책상 정상) | 2026-05-25 21:28 |

## 백업 상태

| 항목 | 값 |
|---|---|
| 최신 백업 | 2026-05-25T04:00 (baduk-20260525T040005.db.gz, integrity OK, 약 17h) |
| daily / weekly / monthly | 5 / 1 / 0 |

## 콘텐츠 인덱스

| 항목 | 값 |
|---|---|
| 프로 기보 수 | 911 |
| 테마 수 | 6 |
| 월간 픽 URL | 14 (최근 12개월 + 현재 + 다음 달) |
| sitemap URL 수 | 937 (정적 5 + 프로 911 + 테마 6 + 픽 인덱스 1 + 월간 픽 14) |
| 최근 CWI ingest | 2026-05-23 (fetched=0 new=0) |
| 이 달의 명국 | 353 |
| 글로서리 | 2/10 |
| FAQ | 1/5 |
| sitemap 글로서리·FAQ URL | 5 (글로서리 3 + FAQ 2) |

## 분석

| 항목 | 값 |
|---|---|
| 최근 주간 리포트 | 2026-W21.md |
| 누적 리포트 수 | 1 |

## 개발 현황

| 항목 | 값 |
|---|---|
| 열린 이슈 | 0건 |
| 열린 PR | 1건 (#30 `last_seen_at` 디바운스 — CI 모두 SUCCESS, MERGEABLE/CLEAN) |

## 보류 승인

`state/pending-approvals.md` 참조 — 2건. AP-20260525-01 (chuk 글로서리 게시,
content-draft 사이클이 등록) / AP-20260525-02 (PR #30 머지 — `database is locked`
누적 2262건 재발 중인 사안의 수정).

## 최근 장애

`state/incidents.md` 참조 — 기존 3건은 복구·정리 완료. 2026-05-25 watchdog 활성화 직후 5건 (WD-20260525-2122*) 자동 기록 — 41시간 무음 정지 사건의 사후 감지로, orchestrator·dev-cycle·content-draft·content-ingest·backup이 stale로 잡혔다. 복구는 사람 결정 대기.

## Watchdog

| 항목 | 값 |
|---|---|
| 잡 등록 | `com.inkbaduk.ops-watchdog` 가동 중 (StartInterval 3600s) |
| 첫 실행 | 2026-05-25 21:22 (수동 kickstart, 신규 incident 5건) |
| 알림 채널 | Telegram (토큰 미설정 → fallback) → macOS notification |
| 임계 | orchestrator 8h · dev-cycle/content-*/backup 30h · analytics-weekly 8d |
| 쿨다운 | 잡당 1시간 1회 |

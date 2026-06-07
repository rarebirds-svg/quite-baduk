# 운영 대시보드

- 갱신: 2026-06-06 18:00

## 스택 상태

| 스택 | 상태 | 마지막 확인 |
|---|---|---|
| prod | 정상 — backend·web 200 OK, db OK, katago_alive:true, 디스크 5%, plist drift 없음. ✅ 배포 갭 해소 — backend가 6/6 17:39:49 재기동(pid **46350**), HEAD(`1ea5246`, #45 머지 이후)에서 가동 → ws.py RuntimeError 가드 라이브. 재기동 이후 신규 RuntimeError 0건 | 2026-06-06 18:00 |
| staging | 중단 (정책상 정상) | 2026-06-06 18:00 |

## 백업 상태

| 항목 | 값 |
|---|---|
| 최신 백업 | 2026-06-06T04:00 (baduk-20260606T040005.db.gz, integrity OK, 7 tables, 약 8h) |
| daily / weekly / monthly | 14 / 2 / 1 |

## 콘텐츠 인덱스

| 항목 | 값 |
|---|---|
| 프로 기보 수 | 1111 (masterpiece 825 + world 286) |
| 테마 수 | 6 |
| 월간 픽 URL | 14 (최근 12개월 + 현재 + 다음 달) |
| sitemap URL 수 | 약 1137 (정적 5 + 프로 1111 + 테마 6 + 픽 인덱스 1 + 월간 픽 14, 재생성 시 갱신) |
| 최근 CWI ingest | 2026-06-06 15:44 (fetched=200 new=200 duplicate=0 error=0, cap=200) |
| 이 달의 명국 | 353 |
| 글로서리 | 11/18 |
| FAQ | 6/9 |
| sitemap 글로서리·FAQ URL | 5 (글로서리 3 + FAQ 2) |

## 분석

| 항목 | 값 |
|---|---|
| 최근 주간 리포트 | 2026-W22.md |
| 누적 리포트 수 | 2 |

## 개발 현황

| 항목 | 값 |
|---|---|
| 열린 이슈 | 0건 — #39(WS RuntimeError)은 2026-06-05 22:37 PR #45 머지로 close. ✅ 6/6 17:39 prod 재기동으로 현 프로세스에 반영(배포 갭 해소). |
| 열린 PR | 0건 — #43 `fix/issue-42-sqlite-pool-size`은 2026-06-07 close(이슈 #42가 오탐·PR #30으로 이미 해소, pool_size=1은 동시성 저하 변경이라 비채택). |

## 보류 승인

`state/pending-approvals.md` 참조 — **0건** (AP-20260606-01은 6/6 17:39 외부 재기동으로 자동 해소·무효 처리).

## 최근 장애

`state/incidents.md` 참조 — 기존 3건은 복구·정리 완료. 2026-05-25 watchdog 활성화 직후 5건 (WD-20260525-2122*) 자동 기록 — 41시간 무음 정지 사건의 사후 감지. 5/27 03:35~17:35 동안 content-draft·content-ingest stale 30건 자동 누적은 watchdog 임계와 plist Weekday 잡 정합성 misalignment에 의한 false-positive였고, 이후 `72ec362`에서 임계를 9d로 정합화. 5/28 04:00 이후 watchdog 신규 incident 0건 — 누적 해소 확인.

## Watchdog

| 항목 | 값 |
|---|---|
| 잡 등록 | `com.inkbaduk.ops-watchdog` 가동 중 (StartInterval 3600s) |
| 첫 실행 | 2026-05-25 21:22 (수동 kickstart, 신규 incident 5건) |
| 알림 채널 | Telegram (토큰 미설정 → fallback) → macOS notification |
| 임계 | orchestrator 18h · dev-cycle/backup 30h · content-draft/content-ingest 9d · analytics-weekly 8d |
| 쿨다운 | 잡당 1시간 1회 |
| 정합성 이슈 | (해소) `72ec362`에서 content-draft·content-ingest 임계를 30h → 9d로 plist 일정과 정합화. 신규 incident 0건 확인. |

# 운영 대시보드

- 갱신: 2026-06-30 18:30

## 스택 상태

| 스택 | 상태 | 마지막 확인 |
|---|---|---|
| prod | 정상 — backend·web 200 OK, db OK, katago_alive:true, 디스크 6%, plist drift 없음. PID api 923 / web 912 ✅ | 2026-06-30 18:30 |
| staging | 중단 (정책상 정상) | 2026-06-30 18:30 |

## 백업 상태

| 항목 | 값 |
|---|---|
| 최신 백업 | 2026-06-30T04:00 (baduk-20260630T040002.db.gz, integrity OK, 7 tables) |
| daily / weekly / monthly | 14 / 6 / 1 |

## 콘텐츠 인덱스

| 항목 | 값 |
|---|---|
| 프로 기보 수 | 1111 (masterpiece 825 + world 286) |
| 테마 수 | 6 |
| 월간 픽 URL | 14 (최근 12개월 + 현재 + 다음 달) |
| sitemap URL 수 | 약 1137 (정적 5 + 프로 1111 + 테마 6 + 픽 인덱스 1 + 월간 픽 14, 재생성 시 갱신) |
| 최근 CWI ingest | 2026-06-28 03:06 (fetched=1237 new=200 duplicate=1037 error=0, cap=200) |
| 이 달의 명국 | 353 |
| 글로서리 | 15/18 |
| FAQ | 7/9 |
| sitemap 글로서리·FAQ URL | 5 (글로서리 3 + FAQ 2) |

## 분석

| 항목 | 값 |
|---|---|
| 최근 주간 리포트 | 2026-W26.md |
| 누적 리포트 수 | 6 |

## 개발 현황

| 항목 | 값 |
|---|---|
| 열린 이슈 | 0건 — bug #53(잘못된 Content-Type → 500)은 6/25 종료(이미 `ce9d745`로 수정·배포된 구버전 기록 오탐). 미분류 0. |
| 열린 PR | 0건 — #47·#50·#52 머지 완료. 주의 PR 없음. |

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

# 방문 통계 운영

## 방문 로그 보존 정리 (retention prune)

`visit_hits`는 방문마다 1행씩 쌓이므로 주기적으로 오래된 행을 지운다.

- 주기: 매일 또는 매주 1회.
- 실행: `cd backend && python -m scripts.prune_visits`
- 동작: 180일(`DEFAULT_RETENTION_DAYS`)보다 오래된 `visit_hits` 행 삭제, 삭제 건수를 structlog로 남긴다. 방문량이 적으면 삭제 0건이어도 정상.
- launchd로 돌릴 경우 `scripts.sync_gsc`와 같은 스케줄 슬롯에 이어 붙이면 된다.

## 국적·순방문자 정확도 전제 — `cf_trusted_proxy`

방문 국가(`country`)와 IP 해시는 Cloudflare가 붙여 주는 `CF-IPCountry`·`CF-Connecting-IP` 헤더에서 뽑는다. prod에서 `CF_TRUSTED_PROXY=true`(`~/.baduk.env`)가 **반드시** 설정돼 있어야 한다.

- 미설정이면 `client_country`가 `None`, `client_ip`가 `"unknown"`으로 떨어져 **모든 방문이 국적 미상·순방문자 1명으로 뭉친다**. 통계가 무의미해지므로 배포 후 한 번 확인한다.
- 확인: 공개 도메인에서 유입된 실제 방문 몇 건 뒤 `visit_hits`의 `country`가 채워지는지 본다(로컬 직접 요청은 CF 헤더가 없어 항상 `None` — 정상).

## 순방문자(UV) 의미

일일 솔트 해시라 **UV는 일 단위로 정확**하고, 기간 UV는 일별 distinct의 합산 근사다. 대시보드의 "순방문자"는 이 성격을 감안해 읽는다.

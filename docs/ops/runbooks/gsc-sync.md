# 러닝북: GSC 검색어 동기화

- 주기: 매일 1회 (launchd 또는 기존 ops 스케줄러)
- 등급: 🟢 자율
- 목적: 구글 Search Console 검색어 데이터를 방문 통계 DB로 동기화한다.

## 절차

```bash
cd backend && python -m scripts.sync_gsc
```

## 사전 조건

- `~/.baduk.env`에 `GSC_PROPERTY_URL`, `GSC_SERVICE_ACCOUNT_JSON` 설정.
- 서비스 계정을 GSC 속성(Search Console property) 사용자로 추가.

두 환경변수가 설정되지 않았으면 no-op 로그만 남기고 정상 종료한다(에러 아님).

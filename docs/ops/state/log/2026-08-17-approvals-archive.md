### AP-20260816-01 — 웨이브 1(사이트 활성화) 19커밋 배포: push + 웹 리빌드 + prod 재기동

- 액션: 8/16 08:17 로컬 `main`에 머지된 `worktree-site-activation` 19커밋을 origin에 push하고, 웹 재빌드 + `ops/stack.sh restart prod`로 라이브에 반영(🟡 — 코드 main push + prod 재기동).
- 근거: 사람이 8/16 08:17 fast-forward 머지를 직접 수행했으나(reflog `5fd1113 merge worktree-site-activation`), origin push·빌드·재기동이 없어 **라이브에는 0건 반영**이다. launchd 프로세스(api/web PID 88640/88644)는 8/8 15:48 기동 그대로 옛 코드를 물고 있고 `BUILD_ID`도 8/8 15:48이다. 마이그레이션은 **이미 적용됨** — `alembic_version` = `0019` 실측(0018 닉네임 유니크 폐지 + 0019 analytics_salts). 즉 `site-activation-external.md` 5-5절의 "마이그레이션 선행" 조건은 충족됐고 남은 것은 push·빌드·재기동뿐이다.
- 영향: 90일 슬라이딩 세션·닉네임 중복 허용, `/daily`·`/spectate` 비로그인 개방, 랜딩 원클릭 시작, 콘텐츠 CTA·공유 버튼, `/spectate/pro` SSR, 사이트맵 신규 URL, daily_salt 영속화(67e8c07), 주간 ingest IndexNow 통보(다음 일요일부터)가 일괄 발효. 커뮤니티 홍보(러닝북 3장)의 선행 조건(5장 체크리스트)이 충족 가능해진다.
- 실행 절차:
  1. `git -C /Users/daegong/projects/baduk push origin main` — 19커밋 + ops 로그 커밋 push.
  2. `cd /Users/daegong/projects/baduk/web && npm run build` — 실패 시 기존 `.next` 유지로 중단(재기동 안 함).
  3. `bash /Users/daegong/projects/baduk/ops/stack.sh restart prod`.
  4. `curl -fs http://localhost:8000/api/health` 200 + `curl -fs http://localhost:3000` 200 확인.
  5. 5-3 라이브 스모크(시크릿 창 기준): `/` 원클릭 시작 노출, `/daily`·`/spectate` 비로그인 200, `/spectate/pro` 페이지 소스에 SSR 목록, `sitemap.xml`에 `/daily`·`/spectate`·`/spectate/pro` 포함.
  6. 다음 사이클에서 `sessions` 테이블 적재 시작 여부 확인(90일 세션 발효의 결정적 증거).
- 잔여 위험: 재기동 수십 초 다운타임 — 진행 중 대국 0건(`moves.max(played_at)` 8/11 11:45 UTC, 약 5일 전)이라 낮음. 웹 빌드 실패 시 기존 `.next`로 롤백 가능. 구 코드 + 신 스키마 동거는 안전 확인됨(제약 제거 + 신규 테이블뿐).
- 참고: 커뮤니티 홍보(3장) 집행은 이 배포와 별개의 🟡 — 배포 완료 후 사람이 따로 판단한다.
- **8/16 21:00 재확인 (12시간 무응답)** — 변화 없음: `origin/main..HEAD` 20커밋(코드 19 + ops `bda8f60`) 유지, `BUILD_ID`·PID 8/8 15:48 그대로(197시간 무재기동), `alembic_version` 0019 유지. 위험 재평가 — 오늘 12:45 KST 대국 **#339**(88수)가 발생·종료해 실사용이 재개됐다. 현재 진행 중 대국은 0건이나, 배포 실행 시점에 `moves.max(played_at)` 재확인 후 재기동할 것(절차 불변). 중복 제안은 만들지 않고 이 각주만 누적한다.
- **8/17 09:00 재확인 (48시간 무응답)** — 변화 없음: `origin/main..HEAD` **21커밋**(코드 19 + ops 2 `bda8f60`·`f9e242b`) 유지, `BUILD_ID`·PID 8/8 15:48 그대로(209시간 무재기동), `sessions` 0행 = 90일 세션 미발효 지속. 위험 재평가 — 진행 중 대국 0건(`moves.max(played_at)` 8/16 03:45 UTC, 약 29시간 전)으로 재기동 위험 다시 낮음. 절차 불변, 실행 시점에 진행 중 대국만 재확인. 중복 제안은 만들지 않고 이 각주만 누적한다.
- 상태: 대기 (2026-08-16 09:00 등재 · 2회 재확인 — 8/16 21:00 · 8/17 09:00)

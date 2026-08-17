# 승인 대기 큐

🟡 액션 제안이 여기 쌓인다. 형식은 `runbooks/telegram-protocol.md` 참조.
처리 완료 항목은 큐에서 제거하고 `state/log/`로 옮긴다.

## 대기 중

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

## 처리 완료 — 최근

### AP-20260808-01 + AP-20260805-01 — 처리 완료(사람 승인 · 에이전트 실행, 2026-08-08 15:47~15:49 KST)

두 건을 한 묶음으로 실행해 **#75·#77·#79 세 건이 한 번의 재기동으로 함께 발효**했다. AP-20260805-01은 제안 후 **75시간**, 재확인 7회 만의 해소다. 원문은 [`log/2026-08-08-approvals-archive.md`](log/2026-08-08-approvals-archive.md)로 옮겼다.

- **1단계 머지 완료** — `gh pr merge 79 --squash --delete-branch` → `eb12635`, `mergedAt` `2026-08-08T06:47:38Z`. 로컬 브랜치 삭제만 실패했다(`.worktrees/dev-cycle`가 `fix/issue-78` 점유 중) — 원격 브랜치는 삭제됐고 dev-cycle 워크트리는 의도적으로 건드리지 않았다.
- **2단계 pull 완료** — `git pull --ff-only` `a59b260..eb12635` fast-forward, 10파일 +195/−45. **이 단계가 핵심이었다** — 빠뜨리면 재빌드가 #79 없는 트리에서 돌았다. 로컬 미커밋(`docs/ops/state/*`·`e2e/*`)과 유입 파일 집합의 교집합은 공집합임을 사전 실측했다.
- **3단계 웹 빌드 완료** — `npm run build` 성공, `web/.next/BUILD_ID` mtime `8/4 22:23` → **`8/8 15:48`**. 5일간 고정돼 있던 값이 처음 갱신됐다.
- **4단계 재기동 완료** — `ops/stack.sh restart prod`. api PID **93501 → 88640**, web **93522 → 88644**, 둘 다 `lstart` = `2026-08-08 15:48:51`. **133시간 50분(5일 14시간) 무재기동 구간이 끝났다.** 재기동 직전 DB 재확인 `max(id)`=337 · 마지막 수 `2026-08-06 13:04:14 UTC`(약 45시간 전)로 중단될 진행 중 대국 0건을 확인했다(`[[in-progress-game-detection]]`).
- **5단계 헬스 확인** — backend `{"status":"ok","db":true,"katago_alive":true}` 200, web :3000 200.
- **판별 검사 3종 전부 통과.**
  - **#77 발효** — `grep -rl 'resultText' web/.next/{static,server}` = **0개 → 17개 파일**. 7회 재확인 동안 0이던 값이다.
  - **#79 발효** — `grep -rl 'authFailure|sessionExpired' web/.next/{static,server}` = **13개 파일**.
  - **#75 발효** — 새 기동 블록(`baduk-web.log` `8/8 15:48`, `▲ Next.js 14.2.35` / `✓ Ready in 137ms`)에 standalone 경고가 **없다**. `baduk-web.err`에서 재기동 후 늘어난 것은 **2줄뿐이며 둘 다 신규 PID 88656의 무해한 `--localstorage-file` Node 경고**다(line 11부터 39회 반복되는 상시 기동 경고). standalone 경고의 마지막 발생은 여전히 **line 2929**로, 그 뒤 200줄이 전부 재기동 이전 구간이다. `web/.next/standalone` 디렉터리도 생성되지 않았고(불필요 번들 소멸) `next.config.js`에 `output` 지정이 없음도 확인했다.
  - **판정 방법 메모 — 종전 절차로는 판정이 불가능했다.** stderr에는 기동 배너가 남지 않는다(stdout으로 감). 따라서 "`.err` 새 기동 블록에 경고가 없으면"은 `.err` 단독으로 성립하지 않는다. **`.err` mtime으로 대체하려는 시도도 틀렸다** — 새 프로세스가 위 Node 경고를 쓰기 때문에 mtime은 결국 갱신된다(실제로 `06:25`→`15:50`으로 바뀌어 중간 판정을 정정했다). 올바른 방법은 **① `baduk-web.log`의 새 기동 배너 확인 ② `.err` 신규 라인의 PID가 새 프로세스인지 보고 그 내용이 무엇인지 읽기 ③ 빌드 산출물 교차 확인**(`.next/standalone` 부재 + 신규 심볼 grep)이다(`[[api-log-stdout-vs-stderr]]`의 웹 판본).
- **라이브 스모크** — `/`·`/spectate`·`/spectate/pro`·`/spectate/pro/1`·`/glossary`·`/history` **전부 200**.
- **부수 해소 확인** — 재기동 전 `.err` 말미에 쌓여 있던 `Failed to find Server Action. This request might be from an older or newer deployment.` 다발(라인 3097~3119)은 8/2 기동 프로세스가 8/4에 통째로 갈린 `.next`를 물고 있던 메모리·디스크 불일치의 증상이다. 전부 재기동 **이전** 구간이며 새 프로세스에서는 재발하지 않았다.

### AP-20260802-01 — 처리 완료(사람 수동 실행, 2026-08-02 22:10~22:11 KST)

제안 후 약 10시간 만에 사람이 실행 절차 1~3단계를 수행했다. 8/3 12:00 세션이 **6단계 판별 검사를 포함해 4건 전부를 라이브 실증**했다.

- **1단계 pull 완료** — `git rev-list --count HEAD..origin/main` = **0**, 작업 트리 HEAD = `fe4d755` = `origin/main`. 배포 갭 해소.
- **2단계 웹 빌드 완료** — `web/.next/BUILD_ID` mtime **8/2 22:10**.
- **3단계 재기동 완료** — api PID **512 → 93501**, web **497 → 93522**, 둘 다 `ps lstart` = `Sun Aug 2 22:11:37 / 22:11:42`. 이로써 4일 18시간 이어지던 무재기동 구간이 끝났다.
- **4단계 헬스 확인** — backend `{"status":"ok","db":true,"katago_alive":true}` 200, web 200.
- **5단계 검증** — 프로 기보 상세 `/spectate/pro/1` **200**, `/api/spectate/pro?limit=1` 정상 JSON. 용어집 `/glossary` 200, `/glossary/sahwal`에 **`<svg>` 3개 렌더** = #73 board 다이어그램 렌더러 발효.
- **6단계 결정적 증거 — 통과.** 이번 세션 시작 로그(`orchestrator-runs.log` **2026-08-03 12:00:05**)에 `Write(...)` deny 경고 2건이 **처음으로 사라졌다**(8/2 12:00·18:00 두 사이클 연속 재출력되던 것). `.claude/settings.json` 실측도 `Edit(/Users/daegong/projects/baduk/backend/data/*.db)`·`Edit(.../katago/models/*)`로 확인 = **#71 발효**. 11일간 실효 없던 prod DB·KataGo 모델 가드레일이 살아났다(`[[settings-deny-write-vs-edit]]`).
- **#72 발효** — 새 `ops/check-staleness.sh`가 이번 사이클에 정상 실행(`신규 incident 0건`). 성공 마커 기준 판정으로 전환됐다.
- **#66 발효 + 부하 실증** — 재기동 후 14시간 동안 `.err` 트레이스백 **0건**(현 기동 마커 line 225406 이후 총 4줄 = uvicorn 기동 라인뿐). 같은 구간 프로 상세 요청은 최근 2,000줄 중 **1,158건**으로 관측 이래 최고 밀도인데 **5xx 0건**이다. 배포 직전까지 누적되던 `database is locked`(마지막 발생 line 225347)는 전부 현 기동 *이전* 구간이다.

### AP-20260802-01 (원문 보존)
- 액션: 8/1 23:00에 머지된 4커밋을 prod에 배포 — prod 작업 트리 `git pull` + 웹 재빌드 + `ops/stack.sh restart prod`.
- 근거: **사람이 8/1 23:00 KST에 PR #66·#71·#72(+ #73)를 전부 머지했으나, prod 작업 트리는 아직 `38fd9e3`으로 `origin/main`(`fe4d755`) 대비 4커밋 behind다. 즉 머지된 4건 중 라이브에 반영된 것은 0건이다.** launchd prod는 리포 작업 트리에서 직접 구동되므로(`[[prod_runs_on_launchd]]`) 머지만으로는 아무것도 바뀌지 않는다. 실증 — 이번 세션 시작 로그(`orchestrator-runs.log` 12:00:05)에 #71이 고치기로 한 `Write(...)` deny 경고 2건이 **여전히 그대로** 출력됐다.
- 영향: 머지된 4건이 실제로 동작하기 시작한다.
  - `#71` `.claude/settings.json` — deny 규칙 `Write(...)`→`Edit(...)`. **`git pull`만으로 즉시 발효**(하네스가 작업 트리에서 읽음). prod DB·KataGo 모델 가드레일이 11일 만에 실효를 갖는다.
  - `#72` `ops/check-staleness.sh` — watchdog 신선도 판정을 "마지막 성공 종료 마커" 기준으로 전환. **`git pull`만으로 다음 정시 실행부터 발효**. OPS-20260728-01류 크래시 루프 무음 사각지대가 닫힌다.
  - `#66` `backend/app/api/spectate_pro.py` — 프로 기보 조회수 원자적 UPDATE + 락 실패 흡수. **backend 재기동 필요.**
  - `#73` `web/lib/board-svg.ts`·`web/lib/content.ts` — 용어집 board 다이어그램·이미지 figure 렌더링. **웹 재빌드 + 재기동 필요.** 콘텐츠 목록은 `force-dynamic`이지만 신규 렌더러는 번들에 들어가야 하므로 `npm run build` 없이는 반영되지 않는다.
- 검증 상태: `git diff --stat HEAD origin/main` = 9파일 675+/26- (backend 2 · ops 2 · web 4 · `.claude` 1). **충돌 없음** — 로컬 미커밋 변경(`docs/ops/state/*`, `e2e/*`)과 유입 파일 집합의 교집합이 공집합임을 실측했다. 4커밋 전부 머지 시점 CI 4잡 SUCCESS.
- 잔여 위험: 재기동 중 수십 초 다운타임. 현재 대국 경로 트래픽은 최근 1,600줄에서 진행 중 대국 0건(마지막 대국 #336은 8/1 19:15 KST 종료)이라 대국 중단 위험은 낮다. 웹 빌드 실패 시 기존 `.next`가 남아 있어 롤백은 재기동만으로 가능하다.
- 실행 절차:
  1. `git -C /Users/daegong/projects/baduk pull --ff-only` — `38fd9e3` → `fe4d755`. (여기까지만 해도 #71·#72는 발효한다.)
  2. `cd /Users/daegong/projects/baduk/web && npm run build` — #73 렌더러 번들 반영.
  3. `ops/stack.sh restart prod` — backend(#66)·web(#73) 재기동.
  4. `curl -fs http://localhost:8000/api/health` 200 + `curl -fs http://localhost:3000 >/dev/null` 200 확인.
  5. 프로 기보 상세 1건 GET 200 확인, 용어집 다이어그램 페이지 1건 육안 확인.
  6. 다음 오케스트레이터 실행에서 `orchestrator-runs.log`에 `Write(...)` deny 경고 2건이 **사라졌는지** 확인 — #71 발효의 결정적 증거다.
- 상태: **완료 (8/2 22:11 사람 수동 실행 · 8/3 12:00 검증)**
- **8/2 18:00 재확인 (6시간 무응답)** — 배포 갭 변화 없음(`38fd9e3` vs `fe4d755`, 4커밋 behind 유지). 6번 항목의 판별 검사를 실제로 수행했고, `orchestrator-runs.log` **18:00:05**에 `Write(...)` deny 경고 2건이 **그대로 재출력**됐다 = #71 미발효 확정. 중복 제안은 만들지 않고 이 항목을 유지한다. 참고로 같은 6시간 구간 프로 상세 트래픽은 144건(24건/h, 관측 이래 최고)인데 5xx 0건이라, #66 미배포로 인한 라이브 위험은 낮은 편이다 — 배포 긴급도는 #71·#72(가드레일·watchdog 사각지대) 쪽이 더 높다.

## 처리 완료

### AP-20260730-01 — 처리 완료(사람 머지, 8/1 23:00 KST)
PR #72(watchdog 성공마커 판정, 이슈 #70) 머지됨 — `fe4d755`. 제안 후 89시간. **다만 prod 작업 트리 미반영이라 라이브 발효는 안 됐다 — AP-20260802-01로 승계.**

### AP-20260725-01 — 처리 완료(사람 머지, 8/1 23:00 KST)
PR #66(프로 기보 조회수 원자적 UPDATE, 이슈 #65) 머지됨 — `fd68fa3`. 제안 후 189시간(7.9일), PR 감시 "정체" 2사이클 집계 후 해소. **backend 재기동 전까지 라이브 미반영 — AP-20260802-01로 승계.**

### AP-20260723-01 — 처리 완료(사람 머지, 8/1 23:00 KST)
PR #71(`.claude/settings.json` deny `Write`→`Edit`) 머지됨 — `1ca3bcd`. 제안 후 227시간(9.5일). **`git pull` 전까지 경고 2건이 계속 재출력됨을 8/2 12:00 세션에서 실측 — AP-20260802-01로 승계.**

### AP-20260716-01 — 처리 완료(사람 승인·머지)

PR #58 머지 완료.

### AP-20260717-01 — 처리 완료(사람 승인·머지)

PR #60 머지 완료.

### AP-20260606-01 — 무효 처리(자동 해소)

제안 대상이 후속 변경으로 사라져 무효 처리.

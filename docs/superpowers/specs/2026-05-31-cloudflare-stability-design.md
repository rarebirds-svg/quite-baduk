---
date: 2026-05-31
topic: Cloudflare 기반 안정성·SPOF 구조 개선
status: draft
---

# Cloudflare 기반 안정성 구조 개선 — 설계

## 배경

라이브 prod는 맥미니 한 대에서 launchd로 직접 구동된다. cloudflared Tunnel이
아웃바운드로 Cloudflare에 붙어 단일 호스트네임을 경로 분할(`/api/*` → FastAPI
:8000, 그 외 → Next.js :3000)로 서빙한다. KataGo는 맥미니의 네이티브 서브프로세스다.

2026-05-25 watchdog 활성화 직후 드러난 가장 아픈 사건은 **41시간 무음 정지**였다.
전체(콘텐츠·브랜드·SEO 포함)가 같이 죽었고 아무도 몰랐다.

## 근본 제약 (비협상)

**맥미니 SPOF는 "대국 플레이"에 대해 제거 불가능하다.** KataGo가 맥미니의 네이티브
바이너리 서브프로세스(GTP, Metal/CPU)이고 FastAPI 백엔드가 여기에 강결합돼 있다
(`engine_pool` 프로세스 싱글톤, 게임별 `asyncio.Lock`, WebSocket 세션 상태, 로컬
SQLite). Cloudflare Workers/Pages는 영속 서브프로세스도, 로컬 SQLite 파일도, 프로세스에
묶인 장수명 WS 상태도 가질 수 없다. 따라서 대국 기능은 맥미니에 남는다.

→ 현실적 목표는 SPOF *제거*가 아니라 **SPOF의 영향 범위를 대국 기능으로 한정하고,
콘텐츠·브랜드·SEO 표면은 맥미니와 무관하게 24/7 살리는 것**이다.

## 비목표

- KataGo / 대국 백엔드의 Cloudflare 이전 (불가능 — 위 제약)
- Next.js 앱 전체의 Pages 이전(`@cloudflare/next-on-pages`). Edge 런타임 호환
  + 교차 출처 쿠키라는 새 실패면을 들여와 "단순화" 목표와 충돌하므로 채택하지 않음.
- 트래픽/비용 최적화. 현 트래픽은 주 24판 수준으로 무료 티어 한도와 무관하다.

## 현재 사실 (조사 결과)

- `com.baduk.api` / `com.baduk.web` 둘 다 이미 `KeepAlive=true` · `RunAtLoad=true`.
  → 프로세스가 *종료*되면 launchd가 자동 재시작한다. 41h 정지는 단순 크래시가 아니라
  머신 다운(정전·재부팅 후 미로그인) 또는 hung(살아있으나 응답 불능)이었을 가능성이 크다.
- 현 watchdog(`com.inkbaduk.ops-watchdog`)은 **맥미니 위에서** 돈다 → 맥미니가 죽으면
  감시자도 같이 죽는다. 감시자가 SPOF 위에 있다.
- 콘텐츠 데이터 출처:
  - 글로서리·FAQ → 리포 내 마크다운(`web/lib/content`, fs 읽기). `force-dynamic`은
    재빌드 없이 새 md 노출용.
  - 프로 기보 → 백엔드 API/SQLite fetch (`/api/spectate/pro/{id}`).

## 설계 — 2단계

### Phase B — 단일 노드 하드닝 (즉효, 위험 0, 이전 없음)

KeepAlive가 *못 잡는* 4가지 빈틈을 메운다.

**B1. 머신 레벨 자동 복구**
- `sudo pmset -a autorestart 1` — 정전 복구 시 자동 부팅
- `sudo pmset -a sleep 0 disksleep 0 womp 1` — 슬립 금지, Wake-on-LAN 허용
- 자동 로그인 활성화 — 재부팅 후 사람 로그인 없이 GUI launchd 에이전트(`com.baduk.*`,
  cloudflared)가 자동 기동되도록. (cloudflared는 LaunchDaemon이라 로그인 무관하나
  `com.baduk.*`는 GUI 도메인 LaunchAgent이므로 자동 로그인이 필요)
- 검증: 맥미니를 강제 재부팅 → 사람 개입 없이 `/api/health` 200 복귀 확인.

**B2. Hung 프로세스 자동 교정**
현 watchdog은 알림만 한다. HTTP 헬스 실패가 N회 연속(예: 3회/3분)이면 자동으로
`launchctl kickstart -k gui/$(id -u)/com.baduk.api`(및 web)를 실행하도록 watchdog에
자동 교정 단계를 추가. "살아있지만 응답 없음"을 사람 개입 없이 복구한다.
- 안전장치: 쿨다운(잡당 1회/시간 — 기존 패턴 재사용), 재시작 시 incident 기록.
- 검증: uvicorn을 인위적으로 wedge(예: SIGSTOP) → watchdog이 kickstart로 복구하는지 확인.

**B3. 외부 독립 모니터 (SPOF 위의 감시자 제거)**
맥미니 *밖*에서 도는 무료 헬스체크. **Cloudflare Worker Cron Trigger**(무료)가
1~5분 주기로 `https://<domain>/api/health`를 외부에서 폴링 → 실패 시 Telegram 알림.
맥미니가 통째로 죽어도(머신·네트워크·Tunnel 다운) 이 감시자는 살아서 알린다.
- 토큰/챗ID는 Worker secret으로 저장. 기존 `~/.claude/channels/telegram`과 동일 채널.
- 검증: cloudflared를 내려 origin을 죽이고 5분 내 Telegram 알림 수신 확인.

**B4. 정지 중 graceful fallback 페이지**
Tunnel origin이 다운이면 죽은 사이트 대신 정적 "AI 점검 중" 페이지를 노출.
- 구현: Cloudflare Pages에 단일 정적 점검 페이지를 두고, cloudflared ingress의 catch-all
  또는 Cloudflare 커스텀 에러 페이지로 origin-down 시 폴백. (Phase C 도입 시 콘텐츠
  사이트 자체가 폴백 역할을 겸하므로 B4는 C로 자연 흡수됨 — B 단독 적용 시에만 별도 구성)
- 검증: origin down 상태에서 사용자에게 200/503 + 점검 안내 페이지가 보이는지 확인.

### Phase C — 콘텐츠 정적 분리 (SPOF 영향 범위 축소)

라우트를 두 부류로 가른다.

**정적 콘텐츠 (엣지로, 맥미니 무관)**
`/`, `/faq` · `/faq/[slug]`, `/glossary` · `/glossary/[slug]`,
`/spectate/pro` · `/spectate/pro/[id]`, `/spectate/themes/*`, `/spectate/picks/*`,
`/privacy`, `/terms`, `/supporters`, `/support`, `/sitemap.xml`
→ 937 sitemap URL의 거의 전부.

**인터랙티브 (맥미니 유지)**
`/game/*`(new·play·review), `/admin/*`, `/settings`, `/history`,
라이브 `/spectate/[id]`(WS 관전).

#### 도메인 분리

- `inkbaduk.com`(apex) + `www` → **Cloudflare Pages**, 정적 콘텐츠 빌드 산출물.
- `app.inkbaduk.com` → 기존 cloudflared Tunnel → 맥미니 (현 앱 그대로).

도메인 분리를 택한 이유: 단일 호스트네임에서 Pages(정적)와 Tunnel(동적)을 경로로
가르려면 Worker 프록시 레이어가 필요해 복잡도가 늘어난다. 도메인 분리는 인프라가 더
단순하고, **현재 앱의 single-origin 쿠키·WS 모델을 전혀 건드리지 않는다**
(`app.` 서브도메인 내부에서 기존 상대 `API_BASE`·same-origin WS·`SameSite=lax`가 그대로
동작). 정적 콘텐츠 사이트는 인증이 없으므로 쿠키 복잡도가 없다.

#### 정적 생성 전환

- **글로서리·FAQ**: `force-dynamic` 제거 → `generateStaticParams` 기반 SSG. 데이터가
  리포 마크다운이므로 빌드타임에 완결. content-draft가 이미 main에 push → Pages가
  git push에 자동 빌드 → 신규 콘텐츠 ~1–2분 내 반영. (현 "즉시 반영"과 분 단위 지연을
  맞바꾸지만 런타임 SPOF 제거가 그만한 가치)
- **프로 기보**: 빌드타임에 맥미니 백엔드 API에서 fetch(SSG). 신규 CWI ingest(주 단위)는
  rebuild로 반영 — content-ingest 후 Pages deploy hook 트리거 또는 야간 정기 rebuild.
  빌드 시 맥미니가 죽어 있으면 빌드는 실패하되 **Pages는 직전 배포본을 계속 서빙**하므로
  런타임 가용성은 영향 없음.

#### 콘텐츠 ↔ 앱 연결

- 콘텐츠 사이트의 "대국 시작" 등 CTA는 `https://app.inkbaduk.com/...`로 링크.
- 앱 도메인의 헤더/네비에서 콘텐츠로 돌아가는 링크는 apex로.
- SEO: 콘텐츠(SEO 표면)는 apex에 유지하므로 canonical·sitemap 영향 없음. 대국 URL은
  애초에 SEO 대상이 아니다.

## 데이터 흐름 (Phase C 적용 후)

```
방문자 ── apex/www ──► Cloudflare Pages (정적 콘텐츠, 엣지)        [맥미니 무관, 24/7]
방문자 ── app. ──► Cloudflare Tunnel ──► 맥미니 FastAPI :8000 + Next :3000 ──► KataGo
외부감시 ── Worker Cron ──► /api/health ──► (실패 시) Telegram      [맥미니 밖]
```

맥미니 다운 시: 콘텐츠 사이트 정상, 대국만 불가(graceful "점검 중"), 외부 모니터가 알림.

## 비용

전부 무료 티어. Pages(무제한 요청, 500 빌드/월), Worker Cron(무료 한도 내 충분),
Tunnel(무료), R2 백업(현행 유지). 트래픽 주 24판으로 한도와 무관.

## 검증 기준 (성공 정의)

- B1: 강제 재부팅 후 사람 개입 0으로 `/api/health` 200 복귀.
- B2: 프로세스 wedge 주입 시 watchdog이 자동 kickstart로 복구.
- B3: origin 강제 다운 시 5분 내 외부 모니터의 Telegram 알림 수신.
- C: 맥미니를 내린 상태에서 apex의 콘텐츠 URL(글로서리·FAQ·프로 기보) 200 정상 서빙,
  `app.`는 graceful 점검 안내. sitemap/검색 노출 회귀 없음.

## 리스크·트레이드오프

- C 도입 시 콘텐츠 신규 반영이 "즉시"→"분 단위(빌드)"로 바뀐다. 수용 가능.
- 프로 기보 정적 빌드는 빌드타임 맥미니 의존 → 빌드 실패해도 직전 배포본 유지로 완화.
- 도메인 2개 운영 → DNS·CORS 설정 1회성 작업. 단, 앱 내부는 single-origin 유지라
  런타임 CORS 복잡도 없음.
- 자동 로그인 활성화는 물리 보안을 일부 낮춘다(맥미니가 가정 내부망이라 수용 가능).

## 단계 적용 순서

B1 → B2 → B3 → (B4는 C로 흡수) → C. B는 각각 독립 적용·검증 가능하며, C 없이도
하드닝만으로 즉시 가용성이 오른다.

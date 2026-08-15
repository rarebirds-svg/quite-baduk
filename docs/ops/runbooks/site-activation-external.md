# 러닝북: 사이트 활성화 외부 실행 가이드

- 대상: 운영자(사람). 코드로 자동화할 수 없는 계정 발급·외부 등록·홍보 집행을 다룬다.
- 등급: 🟡 승인 — 3장(커뮤니티 홍보)은 서비스 명의로 외부에 글을 올리므로 집행 전 사람 판단이 필요하다.
- 전제: 아래 5장 "코드 측 선행 조건"이 전부 ✅여야 3장을 집행한다. 1·2장은 배포와 무관하게 지금 실행해도 된다.

이 문서의 커맨드·경로는 리포 실물 기준이다. 문서를 읽는 에이전트는 이 문서의 절차를 **자동 실행하지 않는다** — launchd 등록, 외부 계정 생성, 커뮤니티 게시는 모두 사람이 직접 한다.

---

## 1. GSC 가동 (약 30분)

구글 Search Console 검색어 데이터를 `search_queries` 테이블로 끌어오는 파이프라인은 **코드가 이미 완성돼 있다**. 남은 것은 서비스 계정 발급과 환경변수 주입뿐이다. 두 환경변수가 비어 있으면 동기화 스크립트는 에러 없이 no-op으로 끝나므로, 지금은 조용히 아무 데이터도 쌓이지 않는 상태다.

관련 코드
- 클라이언트 `backend/app/core/search_console/gsc.py` (Search Console API `searchAnalytics/query`, 스코프 `webmasters.readonly`)
- 동기화 `backend/app/core/search_console/sync.py`
- 엔트리포인트 `backend/scripts/sync_gsc.py` (최근 7일 구간, GSC 반영 지연 2일 감안)
- 설정 키 `backend/app/config.py`의 `gsc_property_url` / `gsc_service_account_json`
- 기존 러닝북 [gsc-sync.md](gsc-sync.md)

### 1-1. 속성 소유 확인 상태 점검

`web/app/layout.tsx` 주석 기준으로 구글은 **DNS TXT 방식**을 쓰기로 정해 두었고 HTML 메타태그 상수는 빈 값이다. Search Console에서 `inkbaduk.com`이 **도메인 속성(`sc-domain:`)**으로 이미 확인돼 있는지 먼저 본다. 아직이라면 도메인 속성으로 추가하고 안내받은 TXT 레코드를 Cloudflare DNS에 등록한다.

주의. canonical 도메인은 `inkbaduk.com`이다(www 아님). URL 접두어 속성(`https://www.inkbaduk.com/`)으로 만들면 데이터가 갈라진다.

### 1-2. GCP 서비스 계정 생성

1. [console.cloud.google.com](https://console.cloud.google.com)에서 프로젝트를 하나 만든다(기존 프로젝트 재사용 가능).
2. **API 및 서비스 → 라이브러리**에서 `Google Search Console API`를 사용 설정한다.
3. **IAM 및 관리자 → 서비스 계정 → 서비스 계정 만들기**. 이름은 `inkbaduk-gsc-reader` 정도. 프로젝트 역할은 부여하지 않아도 된다 — 권한은 GCP가 아니라 Search Console 쪽에서 준다.
4. 만든 계정의 **키 → 키 추가 → 새 키 만들기 → JSON**. 파일이 바로 내려받아진다.
5. 계정 이메일(`...@....iam.gserviceaccount.com` 형태)을 복사해 둔다.

### 1-3. Search Console 속성에 서비스 계정 추가

Search Console → `inkbaduk.com` 속성 → **설정 → 사용자 및 권한 → 사용자 추가**. 위에서 복사한 서비스 계정 이메일을 **제한됨(Restricted)** 권한으로 추가한다. 읽기 전용 스코프만 쓰므로 소유자 권한은 필요 없다.

### 1-4. 키 저장과 환경변수 주입

키 파일을 리포 바깥의 안전한 경로에 둔다. 리포 안에 두면 커밋 사고가 난다.

```bash
mkdir -p ~/.secrets
mv ~/Downloads/<다운로드된-키>.json ~/.secrets/inkbaduk-gsc.json
chmod 600 ~/.secrets/inkbaduk-gsc.json
```

`~/.baduk.env`에 두 줄을 추가한다(prod 백엔드와 ops 래퍼가 공통으로 읽는 파일이다).

```bash
GSC_PROPERTY_URL=sc-domain:inkbaduk.com
GSC_SERVICE_ACCOUNT_JSON=/Users/daegong/.secrets/inkbaduk-gsc.json
```

`GSC_SERVICE_ACCOUNT_JSON`은 JSON 본문이 아니라 **키 파일 경로**다(`gsc.py`가 `from_service_account_file`로 읽는다). 경로는 `~` 확장이 보장되지 않으므로 절대경로로 적는다.

### 1-5. 수동 1회 실행

```bash
cd /Users/daegong/projects/baduk/backend
set -a; . ~/.baduk.env; set +a
.venv311/bin/python -m scripts.sync_gsc
```

기대 출력은 `gsc_sync_done rows=<N>` structlog 한 줄이다. `gsc_sync_skip reason=no_rows_or_not_configured`가 나오면 둘 중 하나다 — 환경변수가 안 먹었거나(오타·경로), 속성에 아직 노출 데이터가 없다. 전자는 같은 셸에서 `.venv311/bin/python -c "from app.config import settings; print(settings.gsc_property_url, settings.gsc_service_account_json)"`로 갈라낸다(두 값이 비어 있으면 환경변수 문제다). HTTP 403이 뜨면 1-3의 사용자 추가가 아직 반영 전이다(수 분 걸린다).

### 1-6. launchd 일 1회 등록

기존 잡들은 전부 `ops/*.sh` 래퍼 + `ops/launchd/com.inkbaduk.*.plist` 쌍 구조다. GSC도 같은 형식을 따른다. 아래 두 파일을 **운영자가 직접 생성**한다 — 이 리포에는 아직 없다. 미리 커밋해 두면 `ops/sync-launchd.sh`가 다음 사이클에 자동 등록해 버려서, 키가 준비되기 전에 잡이 돌기 시작한다.

`ops/sync-gsc.sh` (`ops/prune-visits.sh`와 동형)

```bash
#!/usr/bin/env bash
# launchd가 매일 호출 — 구글 Search Console 검색어 통계를 DB에 동기화한다.
set -euo pipefail
# launchd는 로그인 셸 PATH를 상속하지 않는다 — Homebrew 경로를 명시적으로 앞에 붙인다.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT/backend"
[ -f "$HOME/.baduk.env" ] && { set -a; . "$HOME/.baduk.env"; set +a; }

RUNLOG="$ROOT/docs/ops/state/log/sync-gsc-runs.log"
mkdir -p "$(dirname "$RUNLOG")"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] sync-gsc 시작" >> "$RUNLOG"
.venv311/bin/python -m scripts.sync_gsc >> "$RUNLOG" 2>&1 \
  || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] sync-gsc 종료" >> "$RUNLOG"
```

```bash
chmod +x /Users/daegong/projects/baduk/ops/sync-gsc.sh
```

`ops/launchd/com.inkbaduk.sync-gsc.plist` (`com.inkbaduk.prune-visits.plist`와 동형, 04:15 prune과 겹치지 않게 05:10)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- 매일 05:10 구글 Search Console 검색어 통계를 동기화하는 launchd 작업. -->
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.inkbaduk.sync-gsc</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/daegong/projects/baduk/ops/sync-gsc.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>5</integer>
    <key>Minute</key><integer>10</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/sync-gsc.out.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/sync-gsc.err.log</string>
</dict>
</plist>
```

등록은 리포의 plist를 `~/Library/LaunchAgents/`로 복사하고 `launchctl bootstrap`까지 해 주는 동기화 스크립트로 한다.

```bash
bash /Users/daegong/projects/baduk/ops/sync-launchd.sh --check   # MISSING com.inkbaduk.sync-gsc.plist 확인
bash /Users/daegong/projects/baduk/ops/sync-launchd.sh           # 실제 설치 + bootstrap
launchctl list | grep inkbaduk.sync-gsc                          # 등록 확인
```

`--check`는 드리프트만 보고하고 exit 1로 끝난다(설치하지 않는다). plist를 나중에 고치면 `ops/sync-launchd.sh`를 다시 돌려 bootout → 재bootstrap 시킨다.

### 1-7. 검증

```bash
sqlite3 /Users/daegong/projects/baduk/backend/data/baduk.db \
  "SELECT COUNT(*) FROM search_queries WHERE source='google';"
```

0이 아니면 성공이다. 상위 검색어까지 눈으로 보려면 아래를 쓴다.

```bash
sqlite3 /Users/daegong/projects/baduk/backend/data/baduk.db \
  "SELECT query, clicks, impressions, ROUND(position,1) FROM search_queries
   WHERE source='google' ORDER BY impressions DESC LIMIT 20;"
```

브라우저에서는 관리자 닉네임 세션으로 로그인한 뒤 `/admin/analytics` 하단 검색어 표에서 같은 데이터를 본다. 다음 날 05:10 이후 `docs/ops/state/log/sync-gsc-runs.log`에 시작·종료 줄이 남았는지 한 번 더 확인하면 자동화까지 끝난 것이다.

---

## 2. 네이버 서치어드바이저

네이버는 GSC와 달리 공개 API가 없어 **CSV 수동 업로드** 경로로 설계돼 있다. 소유 확인은 이미 끝났다 — `web/app/layout.tsx`의 `NAVER_SITE_VERIFICATION` 상수에 토큰이 박혀 있어 `naver-site-verification` 메타태그가 출력된다.

### 2-1. 검색어 리포트 내려받기

1. [searchadvisor.naver.com](https://searchadvisor.naver.com) 로그인 → **웹마스터 도구** → 사이트 `inkbaduk.com` 선택.
2. **리포트 → 검색 키워드**(사이트로 유입된 검색어·클릭·노출·CTR).
3. 기간을 지난 7일로 잡고 **다운로드(CSV)**.

파서는 `backend/app/core/search_console/naver_csv.py`이고 열 순서를 `검색어, 클릭, 노출, CTR`로 읽는다(헤더 1줄 스킵, BOM 허용, 4번째 열이 없으면 CTR 0). 네이버가 CSV 열 구성을 바꾸면 이 파서를 먼저 고쳐야 한다.

### 2-2. 업로드

관리자 닉네임 세션으로 `/admin/analytics`에 들어가 검색어 섹션의 CSV 업로드 입력에 파일을 넣는다. 성공하면 `N건 반영됨`이 뜬다. 내부적으로 `POST /api/admin/search-queries/import`가 호출되며, **기존 `source='naver'` 행을 전부 지우고 새로 적재하는 스냅샷 교체** 방식이다. 즉 네이버 데이터는 누적이 아니라 "마지막 업로드분"만 남는다 — 추세를 보려면 CSV 원본을 따로 보관한다.

### 2-3. 주간 확인 루틴

주간 분석 리포트(`com.inkbaduk.analytics-weekly`, 매주 일요일 09:00)와 같은 날 붙여서 돌린다.

1. 일요일, 위 2-1~2-2로 지난 7일 CSV를 받아 업로드한다.
2. `/admin/analytics`에서 구글·네이버 검색어를 한 화면에서 비교한다(`source=all`, 90일, 상위 50).
3. 다음 세 가지를 메모한다.
   - **노출은 있는데 클릭이 0에 가까운 검색어** — 페이지는 있으나 제목·설명이 안 먹히는 경우. 해당 글의 `seoTitle`을 손본다.
   - **노출은 있는데 대응 페이지가 아예 없는 검색어** — 콘텐츠 공백. 아래 2-4로 넘긴다.
   - **평균 게재순위(position) 11~30위 검색어** — 조금만 보강하면 1페이지로 올라올 후보. 단 `position`은 구글 행에만 채워지고 네이버 업로드 행은 비어 있다.

### 2-4. 시드 선정(Task F)에 반영하는 방법

콘텐츠 자동 게시 파이프라인은 `docs/ops/content/seed-glossary.yml` / `seed-faq.yml`의 시드를 매주 수·토 02:00(`com.inkbaduk.content-draft`)에 소진한다. 시드가 바닥나면 파이프라인이 조용히 멈춘다 — 실제로 3주간 정지했던 전례가 있다.

반영 절차.

1. 2-3에서 뽑은 "대응 페이지 없는 검색어"를 시드 후보로 적는다.
2. 이미 있는 글과 겹치는지 확인한다. **slug가 아니라 frontmatter의 `title`로 대조한다** — 사활 계열이 slug `sahwal`로 통합된 전례가 있어 slug만 보면 공백을 오판한다.

   ```bash
   grep -h "^title:" /Users/daegong/projects/baduk/web/content/glossary/*.md
   grep -h "^title:" /Users/daegong/projects/baduk/web/content/faq/*.md
   ```
3. 남은 시드 재고를 센다. 파이프라인은 1회에 1편만 게시하므로 주 2편이 나간다 — 두 종류를 합친 미작성 잔량이 8편(4주분) 아래로 떨어지면 보충한다.

   ```bash
   grep -c "slug:" /Users/daegong/projects/baduk/docs/ops/content/seed-glossary.yml
   grep -c "slug:" /Users/daegong/projects/baduk/docs/ops/content/seed-faq.yml
   ls /Users/daegong/projects/baduk/web/content/glossary | wc -l
   ls /Users/daegong/projects/baduk/web/content/faq | wc -l
   ```
4. 기존 항목과 **같은 필드 구조**로 시드를 추가하고, `related`가 기존 글과 이어지게 채운다. 파일 상단 주석의 선정 기준 4가지(입문 검색 의도 · 학습 검색 의도 · AI 검색 의도 · 내부링크 연결)에 맞춰 분포시킨다.
5. 커밋하면 끝이다. 목록 페이지가 `force-dynamic`이라 재빌드·재시작 없이 반영된다.

검색어 데이터가 아직 안 쌓인 초기에는 4번의 선정 기준만으로 시드를 채우고, 데이터가 쌓이는 대로 실측 검색어를 우선순위 앞에 끼워 넣는다.

---

## 3. 커뮤니티 홍보 (웨이브 1 배포 후 집행)

5장 체크리스트가 전부 ✅가 된 다음에 집행한다. 배포 전에 홍보하면 "가입 없이 바로 둔다"는 문구와 실제 화면이 어긋나 첫인상을 날린다.

### 3-0. 선행 단계 — 각 채널 홍보 규정 확인 (건너뛰기 금지)

바둑 커뮤니티는 상당수가 **경쟁 서비스이거나 상업적 홍보를 금지**한다. 규정을 어기면 글 삭제로 끝나지 않고 계정·IP 차단, 심하면 서비스 이름 자체가 낙인찍힌다. 채널마다 아래를 **글을 쓰기 전에** 확인한다.

1. 게시판 상단 공지·이용약관에서 홍보·광고 관련 조항을 찾아 읽는다.
2. 최근 한 달 글 목록에서 유사한 자기 서비스 소개 글이 살아 있는지, 삭제·차단됐는지 본다.
3. 등업·활동 이력 요건이 있으면 먼저 채운다(가입 직후 홍보 글은 거의 자동 삭제된다).
4. 애매하면 운영자에게 먼저 문의한다. 답이 없으면 그 채널은 건너뛴다.

### 3-1. 채널 후보

| 채널 | 성격 | 홍보 규정 리스크 | 권장 접근 |
|---|---|---|---|
| 타이젬 자유게시판 | 국내 최대 온라인 바둑 서비스의 자체 커뮤니티 | **높음** — 경쟁 서비스 홍보로 읽힐 소지가 크다 | 규정 확인 후에도 애매하면 보류. 진행 시 링크 없이 "이런 걸 만들어 봤다"는 후기 톤 |
| 사이버오로 커뮤니티 | 동일하게 바둑 서비스 겸 미디어 | **높음** — 위와 같은 이유 | 위와 동일. 뉴스·칼럼 코너 제보 경로가 있으면 그쪽이 안전 |
| 디시인사이드 바둑 갤러리 | 익명 게시판, 반응이 빠르고 직설적 | 중간 — 홍보 글 자동 필터·삭제가 잦고 링크 첨부가 특히 걸린다 | 완성품 자랑이 아니라 "AI 상대로 접바둑 둘 데 만들었는데 세팅 어떤지 봐 달라"는 피드백 요청 톤 |
| 네이버 대형 바둑 카페 | 실명성·연령대 높음, 입문자 유입 좋음 | 중간~높음 — 카페별 등업 조건과 홍보 전용 게시판 규정이 제각각 | 가입 후 최소 활동 이력을 만들고, 홍보 게시판이 따로 있으면 반드시 거기에만 |
| reddit r/baduk | 영문 국제 커뮤니티 | 중간 — 서브레딧·사이트 전체의 self-promotion 규칙 적용 | **서비스가 한국어 중심임을 본문에 먼저 밝힌다.** UI는 ko/en 이중 언어지만 글로서리·FAQ 본문은 한국어 전용이다. 대국·관전은 언어 장벽이 낮으므로 그 부분만 소구 |

집행 순서 권장. 리스크가 낮고 피드백이 빠른 디시인사이드·reddit에서 먼저 반응을 보고 문구를 다듬은 뒤, 규정 리스크가 큰 타이젬·사이버오로는 마지막에 판단한다.

### 3-2. 준비 문구 초안 ① 체험 소구

사실 근거. 이메일·비밀번호 가입 없이 닉네임만으로 세션이 만들어지고(닉네임 중복 허용), 세션은 브라우저에 90일간 보관되며 방문할 때마다 자동 연장된다. 랜딩에 원클릭 "바로 한 판" 시작 경로가 있고, 판 크기 9·13·19줄과 접바둑을 고를 수 있다. 상대는 KataGo Human-SL 인간형 모델이다.

> **제목 안** — AI랑 접바둑 둘 데가 마땅찮아서 하나 만들었습니다 (가입 없음)
>
> 카타고(KataGo)의 사람 흉내 내는 모델(Human-SL)을 상대로 두는 웹 바둑 사이트를 만들었습니다. 계정 만드는 게 귀찮아서, 이메일·비밀번호 없이 **닉네임만 정하면 바로 한 판이 시작**되게 했습니다. 닉네임은 중복도 됩니다. 세션은 브라우저에 90일 남아 있고 들어올 때마다 자동 연장돼서, 한 번 정해 두면 다시 물어보지 않습니다.
>
> - 9줄·13줄·19줄 중에 고르고, 접바둑도 됩니다
> - 상대 기력을 급수·단으로 골라서 맞춰 둘 수 있습니다
> - 끝나면 그 자리에서 복기로 승부처를 볼 수 있습니다
>
> 아직 다듬는 중이라 어색한 데가 많을 겁니다. 특히 기력 설정이 체감이랑 맞는지가 제일 궁금합니다. 한 판 두어 보시고 어긋난다 싶으면 알려주시면 고치겠습니다.

디시인사이드용으로는 더 짧게 줄이고, 링크는 규정 확인 결과에 따라 본문에 넣을지 댓글로 뺄지 정한다.

### 3-3. 준비 문구 초안 ② 콘텐츠 소구

사실 근거. `pro_games`에 프로 기보 3,300여 국이 적재돼 있고 로그인 없이 `/spectate/pro`에서 볼 수 있다. 글로서리·FAQ는 주 2회(수·토) 한 편씩 자동 게시되며 서로 내부링크로 이어진다. 데일리 퍼즐과 관전도 비로그인으로 열려 있다.

> **제목 안** — 프로 기보 3천여 국이랑 바둑 용어사전 무료로 봅니다 (로그인 없이)
>
> 바둑 공부하다 보면 기보 찾는 데 시간을 다 쓰게 되길래, 퍼블릭 도메인 프로 기보 **3,300여 국**을 모아서 로그인 없이 바로 볼 수 있게 정리했습니다.
>
> - 프로 기보 감상 — 대국자·연도로 찾아 수순대로 따라둘 수 있습니다
> - 바둑 용어사전 — 축, 장문, 촉촉수 같은 용어를 예시와 함께. 서로 링크로 이어져 있어서 하나 보다 보면 옆 개념까지 따라갑니다
> - 데일리 퍼즐 — 오늘의 문제와 랜덤 문제, 둘 다 무료입니다
>
> 셋 다 **가입도 로그인도 필요 없습니다.** 마음에 들면 같은 자리에서 AI랑 한 판 둬 볼 수도 있는데, 그것도 닉네임만 정하면 됩니다.
>
> 용어 설명 중에 틀렸거나 어색한 게 있으면 지적해 주시면 반영하겠습니다.

reddit용으로는 위 내용을 영문으로 옮기되, 첫 문단에 "the site's UI is bilingual but the glossary/FAQ articles are Korean-only" 취지를 명시한다. 기보 감상과 대국은 언어 의존도가 낮다는 점을 함께 적는다.

### 3-4. 집행 후

게시 24~72시간 뒤 `/admin/analytics`의 **유입경로(sources)** 표에서 해당 커뮤니티 도메인이 `referrer_host`로 잡히는지 확인한다. 유입이 있는데 대국으로 이어지지 않으면 랜딩 문구가 아니라 첫 화면 흐름을 의심한다. 어느 채널에 언제 무엇을 올렸는지는 주간 분석 리포트에 남겨 다음 회차와 비교한다.

---

## 4. Play 스토어 재개 판단 기준

**보류한다.** 아래 두 조건을 **동시에** 만족하기 전에는 스토어 등록 작업에 착수하지 않는다.

- 주간 순방문자 **100명 이상**
- 방문 → 대국 전환율 **5% 이상**

근거. 현재 안드로이드 쪽은 Capacitor 앱 셸(`web/android/`)만 존재하고 릴리스 서명 설정(`signingConfigs`)도, 스토어 등록·심사도 전혀 진행된 바 없다. 트래픽이 없는 상태에서 등록 작업에 드는 시간은 그대로 매몰비용이 된다 — 웹에서 사람이 붙는 것을 먼저 확인한다.

측정 쿼리(최근 7일).

```bash
sqlite3 /Users/daegong/projects/baduk/backend/data/baduk.db "
SELECT
  (SELECT COUNT(DISTINCT visitor_hash) FROM visit_hits
     WHERE created_at >= datetime('now','-7 days')) AS uv_7d,
  (SELECT COUNT(*) FROM games
     WHERE started_at >= datetime('now','-7 days')) AS games_7d;
"
```

전환율은 `games_7d / uv_7d`로 읽는다. 주의할 점 두 가지.

- `visitor_hash`는 일일 솔트 기반이라 기간 UV는 일별 distinct의 합산 근사다. 7일 distinct는 실제보다 **크게** 나온다 — 즉 이 전환율은 보수적으로 계산된 값이다.
- `visit_hits` 증가분에는 SSR·크롤러·헬스 프로브가 섞인다. 판단 전에 `/admin/analytics`의 유입경로·국가 분포로 봇 비중을 한 번 걸러 본다.

두 조건을 넘긴 뒤에야 릴리스 키스토어 생성, `web/android/app/build.gradle` 서명 설정, 스토어 등록 정보·정책 문서 작성 순으로 착수한다.

---

## 5. 코드 측 선행 조건 — 웨이브 1 배포 확인 체크리스트

3장(커뮤니티 홍보) 집행 전에 **전부 ✅**여야 한다. 머지는 배포가 아니다 — prod 작업 트리가 pull·재빌드·재시작을 마쳐야 라이브가 바뀐다.

### 5-1. 배포 갭 확인

```bash
cd /Users/daegong/projects/baduk
git fetch origin
git rev-list HEAD..origin/main --count   # 0이어야 한다
git log --oneline -12
```

`git log`에 아래 항목이 모두 보여야 웨이브 1이다.

- [ ] 90일 슬라이딩 세션 + 닉네임 유니크 폐지
- [ ] `/daily` · `/spectate` 비로그인 개방
- [ ] 랜딩 원클릭 "바로 한 판" 시작 경로
- [ ] 콘텐츠 상세 체험 전환 CTA
- [ ] 콘텐츠 상세 공유 버튼
- [ ] 콘텐츠 시드 55편 확충(글로서리 40 · FAQ 15)
- [ ] 주간 CWI ingest 후 신규 기보 URL IndexNow 통보
- [ ] `/spectate/pro` 첫 화면 목록 SSR 전환
- [ ] 사이트맵에 `/daily` · `/spectate` · `/spectate/pro` 추가

### 5-2. 프로세스 상태

```bash
bash /Users/daegong/projects/baduk/ops/stack.sh ps prod
```

backend health와 web `:3000`이 둘 다 OK여야 한다. 코드는 들어왔는데 재시작이 안 됐으면 승인 절차([deploy.md](deploy.md))대로 `ops/stack.sh restart prod`를 거친다. prod web은 `npm start`가 `.next`를 서빙하므로 `npm run build` 없이는 새 코드가 반영되지 않는다.

### 5-3. 라이브 확인 URL (브라우저 시크릿 창 — 비로그인 상태로)

| URL | 확인할 것 |
|---|---|
| https://inkbaduk.com/ | 상단에 원클릭 "바로 한 판" 시작 경로가 보인다 |
| https://inkbaduk.com/daily | 로그인 요구 없이 오늘의 퍼즐이 뜬다 |
| https://inkbaduk.com/spectate | 로그인 요구 없이 목록이 뜬다 |
| https://inkbaduk.com/spectate/pro | 목록이 보이고, **페이지 소스 보기**에 기보 항목이 HTML로 들어 있다(SSR 확인 — 빈 껍데기면 실패) |
| https://inkbaduk.com/glossary | 최근 게시글이 올라와 있다 |
| 글로서리 글 아무거나 | 본문 아래 대국 시작 CTA와 공유 버튼이 보인다 |
| https://inkbaduk.com/sitemap.xml | `/daily` · `/spectate` · `/spectate/pro`가 포함돼 있다 |

시크릿 창을 쓰는 이유는 기존 세션 쿠키 때문에 비로그인 개방 여부를 잘못 판정하지 않기 위해서다.

### 5-4. 콘텐츠 파이프라인 재가동 확인

시드 확충 후 첫 수요일 또는 토요일 02:00이 지난 뒤 새 글이 실제로 올라왔는지 본다.

```bash
tail -20 /Users/daegong/projects/baduk/docs/ops/state/log/content-draft-runs.log
ls -t /Users/daegong/projects/baduk/web/content/glossary | head -5
```

---

## 참고 문서

- [gsc-sync.md](gsc-sync.md) — GSC 동기화 잡 자체의 운영
- [visit-analytics-ops.md](visit-analytics-ops.md) — 방문 통계 보존 정리와 UV 해석 주의점
- [deploy.md](deploy.md) — staging → prod 승급 절차
- [healthcheck.md](healthcheck.md) — 상시 헬스체크

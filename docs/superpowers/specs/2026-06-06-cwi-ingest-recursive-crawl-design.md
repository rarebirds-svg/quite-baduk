# CWI 주간 ingest 재귀 크롤 정상화 설계

작성일. 2026-06-06
상태. 설계 승인 완료 (A안 — 재귀 크롤 + 적재 상한 + recent 매핑)

## 배경

주간 ingest 잡(`com.inkbaduk.content-ingest`, 일 03:00)은 에러 없이 실행되지만 시드 이후 **단 한 건도 적재한 적이 없다**(`pro_games`에 `collection='cwi'` 0건). 원인은 크롤 깊이다. `ingest_cwi_weekly.py`의 `extract_sgf_links`는 **CWI 최상위 인덱스 페이지 한 장만** 파싱하는데, 그 페이지에는 `.sgf` 직접 링크가 없고 하위 디렉터리 링크(`games/<기전>/`)만 있다. 실제 SGF는 `…/go/games/games/<기전>/[<NN>/]<파일>.sgf`처럼 2~3단계 아래에 있다(예: `Agon/01/4.sgf`). 기전 디렉터리 117개, 수천 국 규모.

별개로, 적재 시 `collection="cwi"`로 태깅하지만 공개 관전 탭은 `masterpiece/world/recent`만 노출해 **cwi 적재분은 UI에 보이지 않는다.**

## 목표 / 비목표

- **목표**: 주간 watcher 정상화. CWI top 인덱스가 갱신될 때 하위 디렉터리를 재귀 크롤해 신규(중복 아님) 게임을 적재하고, recent 탭에 노출한다.
- **비목표**: 지금 당장의 대량 일괄 임포트. md5 게이트를 유지해 인덱스 불변인 현재는 아무것도 적재하지 않는다(대량 유입 0). 첫 발화 시에도 회당 적재 상한으로 폭주를 막는다.
- bulk archive(games.tgz) 방식·하위 디렉터리별 변경 추적은 채택하지 않는다(YAGNI).

## 데이터 흐름

```
top 인덱스 fetch
  → index_changed() md5 게이트 (불변이면 즉시 종료 — 현행 유지)
  → 변경 시: crawl_sgf_links() 재귀 (깊이·페이지 상한, visited-set)
  → 각 .sgf: fetch → parse_pro_sgf → content_hash 중복 차단
  → 신규 적재, summary["new"] == MAX_NEW_PER_RUN 도달 시 조기 중단
  → save_index_hash()
```

## 컴포넌트별 설계

### 백엔드 — `backend/scripts/ingest_cwi_weekly.py`

상수 추가.
- `MAX_DEPTH = 4` — 인덱스 기준 재귀 최대 깊이(`games/<기전>/<NN>/` 커버).
- `MAX_PAGES = 500` — 1회 크롤이 가져올 디렉터리 페이지 수 상한(서버 예의·폭주 방지).
- `MAX_NEW_PER_RUN = 200` — 1회 신규 적재 상한.

함수.
- `extract_subdir_links(html, base_url) -> list[str]` (신규) — href 중 `/`로 끝나고 `is_cwi_url`을 통과하는 절대 URL만, 순서 보존 dedup. 부모(`../`)·쿼리 정렬 링크(`?C=…`)는 제외.
- `crawl_sgf_links(http, start_url, *, max_depth, max_pages) -> list[str]` (신규) — BFS. `visited: set[str]`로 루프 방지, 페이지 카운터가 `max_pages` 도달 시 중단. 각 페이지에서 `extract_sgf_links`로 `.sgf` 수집 + `extract_subdir_links`로 다음 깊이 큐잉. `.sgf` URL 순서 보존 dedup 반환. 페이지 fetch 실패는 `cwi.dir.fetch_failed` 경고 후 계속.
- 기존 `extract_sgf_links`(단일 페이지)·`is_cwi_url`·`index_changed`·`save_index_hash`·`_build_pro_game`는 유지.

`main_async` 변경.
- 게이트 통과 후 `links = await crawl_sgf_links(http, CWI_INDEX_URL, max_depth=MAX_DEPTH, max_pages=MAX_PAGES)` 로 교체(기존 단일 페이지 `extract_sgf_links` 호출 대체).
- 적재 루프에서 신규 1건 추가될 때마다 `summary["new"]` 검사 → `MAX_NEW_PER_RUN` 도달 시 루프 중단하고 `log.info("cwi.ingest.capped", cap=MAX_NEW_PER_RUN)`.
- 나머지(중복/에러 카운트, commit, save_index_hash, complete 로그)는 현행 유지.

### 백엔드 — `backend/app/api/spectate_pro.py`

목록(`list_pro_games`)의 컬렉션 필터를 수정. 현재.
```python
if collection in ("masterpiece", "recent", "world"):
    filters.append(ProGame.collection == collection)
```
변경 — `recent` 요청은 `recent`+`cwi`를 함께 포함.
```python
if collection == "recent":
    filters.append(ProGame.collection.in_(("recent", "cwi")))
elif collection in ("masterpiece", "world"):
    filters.append(ProGame.collection == collection)
```
total 카운트와 목록 쿼리는 동일한 `filters`를 쓰므로 자동 일관. 검색(q) 분기는 무관·불변.

### 프론트

변경 없음. 기존 "recent"(최근) 탭이 `collection=recent`로 요청 → 백엔드가 cwi 포함분 반환.

## 테스트

### 백엔드 — `backend/tests/...` (ingest 크롤)
httpx `MockTransport`로 가짜 CWI 트리 구성(인덱스 → 기전 디렉터리 → 중첩 `NN/` → `.sgf`).
- `crawl_sgf_links`가 중첩된 `.sgf`를 전부 찾는다.
- `max_depth` 초과 디렉터리는 방문하지 않는다.
- `max_pages` 도달 시 중단한다.
- 순환 링크(자기참조·부모)가 있어도 visited-set으로 무한루프 없이 종료.
- `extract_subdir_links`가 `?C=N;O=A` 류 정렬 링크·`../`를 제외한다.

### 백엔드 — `backend/tests/api/test_spectate_pro.py`
- `collection=recent` 요청이 `collection='cwi'` 행과 `collection='recent'` 행을 함께 반환하고, `masterpiece`/`world`는 제외한다.

### 적재 상한
- 신규 후보가 상한보다 많을 때 `summary["new"] == MAX_NEW_PER_RUN`에서 멈추고 `cwi.ingest.capped`를 남긴다(MockTransport로 다수 `.sgf` 제공).

### 게이트 회귀
- 인덱스 md5가 캐시와 같으면 크롤하지 않고 `cwi.index.unchanged` 후 종료(기존 동작 보존).

## 엣지·안전

- **현재 무동작**: top 인덱스 불변(md5 일치)이라 배포 후에도 즉시 대량 유입 없음.
- **첫 발화 시**: 인덱스가 바뀌면 그때 크롤·적재되며 회당 ≤ `MAX_NEW_PER_RUN`(200). 상한에 걸려 남은 신규가 있으면 다음 회차가 이어받는다(아래 규칙 참조).
- **상한 초과분 처리 (중요)**: 상한 도달로 중단된 경우 `save_index_hash`를 호출하지 **않는다**. 그래야 다음 회차에 게이트(`index_changed`)가 여전히 True라 다시 크롤해 잔여 신규(이미 적재된 건 content_hash로 중복 차단)를 이어 적재한다. **정상 완주(상한 미도달) 시에만** 인덱스 md5를 저장한다.
- 9x9 등 비표준 크기·핸디캡 게임은 `parse_pro_sgf`가 유효성(크기 9/13/19, 착수 존재)을 검증 — 통과분만 적재.
- 모든 fetch는 CWI 화이트리스트(`is_cwi_url`) 통과분만(라이선스 정책, [[pro-game-sgf-source]]).

## 영향 / 배포

- DB 스키마 변경 없음(마이그레이션 불필요). 코드만.
- 배포 후 즉시 동작 변화 없음(게이트 dormant). 검증은 테스트 + MockTransport로.
- 향후 CWI 갱신 시 자동으로 recent 탭에 신규 노출.

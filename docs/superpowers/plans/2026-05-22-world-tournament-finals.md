# 세계 기전 결승 기보 등록 구현 계획

**목표** — 빅6 세계기전(후지쯔·삼성·LG·잉씨·춘란·도요타)의 결승 대국 ~286국을 퍼블릭 도메인 SGF로 프로 기보에 등록하고, 목록을 페이지네이션으로 브라우징 가능하게 만든다.

**소스** — CWI 컬렉션(homepages.cwi.nl/~aeb/go/games/). 관리자가 명시적으로 퍼블릭 도메인 선언. 도사쿠·슈사쿠 명국선 시드와 동일 출처.

## 결승 식별 규칙 (실측 확정)

| 기전 | 식별 방법 | 수량 |
|------|-----------|------|
| Fujitsu | 최상위 `index.html`의 `<h2>Finals>` 표 SGF 링크 | 23 |
| Samsung | edition 디렉터리의 `F[0-9]+.sgf` | 82 |
| LG | 〃 | 92 |
| Chunlan | 〃 | 38 |
| Toyota | 〃 | 9 |
| Ing | SGF `RO[]`가 `Final N` 패턴 | 42 |

합계 약 286국. 모두 19×19, 핸디캡 0.

## 작업 항목

1. **추출 스크립트** — `backend/scripts/extract_world_finals.py`. CWI `games/` 디렉터리를 인자로 받아 위 규칙대로 결승 SGF를 `backend/data/pro_games/world_finals/`로 복사. 파일명 `{기전}_{edition}_{원본}.sgf`.
2. **백엔드** — `pro_games.collection`에 `world` 값 추가. `list_pro_games`에 `offset` 파라미터와 응답 `total` 추가(페이지네이션). 서버 측 `q` 검색은 이미 구현돼 있음 — 프론트가 사용하도록 전환.
3. **시드** — `seed_pro_games.py`를 (디렉터리, collection) 쌍 리스트로 일반화. `world_finals/` → `world`.
4. **프론트엔드** — `ProGameList` 컬렉션 토글 3-way(명국선·세계기전·최근), 페이지네이션 컨트롤, 검색을 서버 `q`로 전환(현 클라이언트 필터는 페이지 범위만 검색돼 부정확).
5. **i18n** — `spectate.proWorld` 등 신규 키 ko/en 동시 추가.
6. **테스트** — 백엔드 pytest(페이지네이션·world 필터), 웹 vitest. 빌드·배포.
7. **에이전트 QA** — design-token-guardian·korean-copy-qa·visual-qa.

## 결정 메모

- `world` 컬렉션 신설 — 명국선(curated 명국)·최근(admin 업로드)과 성격이 달라 별도 분류. 백엔드·프론트 모두 하드코딩된 `masterpiece|recent`를 확장.
- 결승전이 다전제(삼성·LG·춘란 3번기, 잉씨 5번기)라 한 기전·연도에 2~5행이 생긴다. 같은 EV·기사, result·move_count만 다름 — 의도된 동작.
- F-파일명은 본선 대진표 마지막 열(우승 결정전)에만 쓰임. 예선·3위전은 다른 접두사(P·C·J·K·B 등) — 오염 없음.

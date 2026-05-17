# Inkbaduk — 시각 정체성 & 구현 계획

> 라운드 1 브리프(`2026-05-16-brand-brief.md`)와 후보 평가(`2026-05-16-brand-candidates.md`)에 이어 **Inkbaduk**으로 확정. 본 문서는 시각 정체성 정의와 코드베이스 교체 계획.

## 선정 결과

**브랜드명**: Inkbaduk (잉크바둑)

근거 — 정밀 검증(`general-purpose` 에이전트, 2026-05-17):
- `.com` / `.kr` / `.io` / `.ai` 4개 핵심 TLD 모두 미등록
- Google·Bing 검색 결과 0건 (전 세계 사용 사례 없음)
- USPTO 상표 0건. KIPRIS Class 9·41은 수동 확인 권장 (잔여 리스크)
- 한·일·중 부정 함의 없음
- AlphaGo / DeepMind 시리즈 연상 없음
- "ink"가 Editorial Hardcover 디자인 정체성(종이·서예·먹)과 직결

## 시각 정체성

### 워드마크

이중 표기 정책:
- **헤더·마스트헤드**: `Inkbaduk` (font-serif Newsreader, 영문 단독)
- **부가 표기**: `잉크바둑` (font-sans Pretendard, 한글, 작은 사이즈로 hero/footer에서 보조)
- **OG·이메일·외부 공유**: `Inkbaduk · 잉크바둑`

```
example — 헤더
   ● Inkbaduk     │ VOL. I
   
example — hero
   Inkbaduk
   잉크바둑 · 조용한 승부
```

### 색·타이포

기존 Editorial Hardcover 토큰을 그대로 유지 — 브랜드 교체가 디자인 변경을 의미하지는 않음.
- paper · ink · ink-mute · ink-faint
- oxblood (악센트) · gold (주의·승률) · moss (성공·승착)
- font-serif Newsreader / font-sans Pretendard / font-mono IBM Plex Mono

### 심볼 (BrandMark)

현 SVG (`web/components/editorial/BrandMark.tsx`)는 "한 줄과 교차하는 한 점" — 추상적이라 브랜드명과 독립적으로 사용 가능. **변경 없음**. `aria-label`만 "K-Baduk" → "Inkbaduk"으로 갱신.

### 아이콘 (PWA·Apple Touch)

현재 placeholder 솔리드 컬러. 브랜드 확정 후속으로 디자이너 의뢰 또는 다음 라운드에 별도 디자인 — 본 spec 범위 외.

### OG 이미지

신규 생성 권장 (1200×630). 본 spec에서는 자리만 표시:
- 배경 paper, ink 텍스트 `Inkbaduk` 큰 글자 + 작은 `잉크바둑 · 조용한 승부` + 단순 grid 모티프
- 별도 작업으로 PNG 생성 후 `web/public/og-image.png` 배치 + `app/layout.tsx` metadata 갱신

## 코드 교체 계획

### 변경 파일 (8건)

| 파일 | 변경 |
|---|---|
| `web/app/layout.tsx` | metadata title `K-Baduk:조용한 승부` → `Inkbaduk · 조용한 승부`, template `%s — K-Baduk` → `%s — Inkbaduk`, openGraph title `K-Baduk` → `Inkbaduk` |
| `web/components/TopNav.tsx` | 헤더 텍스트 `K-Baduk` → `Inkbaduk` |
| `web/components/editorial/BrandMark.tsx` | `aria-label="K-Baduk"` → `aria-label="Inkbaduk"` |
| `web/public/manifest.json` | name·short_name·description의 `K-Baduk` 모두 `Inkbaduk`으로. description은 같은 의미로 재작성 (e.g., `Inkbaduk — KataGo Human-SL을 상대로 한 판`) |
| `web/lib/i18n/ko.json` | `app.title` `K-Baduk:조용한 승부` → `Inkbaduk · 조용한 승부` |
| `web/lib/i18n/en.json` | `app.title` → `Inkbaduk · Quiet Game` (또는 사용자 선호) |
| `web/tests/editorial/brand-mark.test.tsx` | `expect.toHaveAttribute("aria-label", "K-Baduk")` → `"Inkbaduk"` |
| `README.md` | 프로젝트 인트로에 K-Baduk 명시 → Inkbaduk으로 (있다면) |

### 변경 범위 밖

- 아이콘 PNG 자산 (별도 작업)
- OG 이미지 (별도 작업)
- 도메인 등록 (사용자 직접)
- KIPRIS 수동 확인 (사용자 직접)
- docs/superpowers/specs 및 plans의 과거 K-Baduk 언급 → 역사적 기록이라 그대로 둠

### 검증

- `npm run lint` / `npm run type-check` / `npm test -- --run` (brand-mark 테스트 PASS 확인)
- `npm run build` 후 LaunchAgent kickstart, `/` `/admin` 라우트 200 + 헤더에 "Inkbaduk" 노출 확인

### 커밋 단위

단일 커밋 권장: `feat(brand): K-Baduk → Inkbaduk` — 8개 파일 모두 한 의미 단위.

## 사용자 측 후속

1. **KIPRIS 수동 조회** — Class 9(소프트웨어), Class 41(엔터테인먼트/게임), Class 28(보드게임) 카테고리 "Inkbaduk" / "잉크바둑" 검색해 동일·유사 등록 없음 확인.
2. **도메인 등록** — `inkbaduk.com` 우선, `inkbaduk.kr` 동시 확보 (한국 시장 우선). `.io / .ai`는 선택.
3. **아이콘·OG 이미지 발주** — 디자이너 의뢰 또는 후속 라운드에서 별도 진행.
4. **Cloudflare Tunnel 라우팅** — 새 도메인 연결 시 `backend/deploy/cloudflared.yml` 갱신.

## 변경 로그

- 2026-05-16 v1 — 초안. Inkbaduk 확정 + 8개 파일 교체 계획.

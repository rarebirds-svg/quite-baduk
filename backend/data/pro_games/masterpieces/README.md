# 명국선 SGF

이 디렉터리에 명국선으로 노출할 프로 기보 SGF 파일(`*.sgf`)을 둔다.

## 조건

- **순수 수순 기보만.** 해설(`C[]`)은 적재 시 자동 제거되지만, 출처가
  퍼블릭 도메인인지 확인하는 책임은 등록자에게 있다.
- 권장 메타 프로퍼티: `PB`/`PW`(기사), `BR`/`WR`(단위), `EV`(기전),
  `DT`(대국일 `YYYY-MM-DD`), `RE`(결과), `SZ`, `KM`.

## 적재

```bash
cd backend && source .venv311/bin/activate && python -m scripts.seed_pro_games
```

멱등이다 — 이미 적재된 기보(정제 SGF 해시 동일)는 건너뛴다.

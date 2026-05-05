# GoGameGuru Weekly Go Problems — Vendored Catalogue

The 420 SGF files under `sgfs/` are the **Weekly Go Problems** archive
maintained by **An Younggil 8p** and **David Ormerod** at
[gogameguru.com](https://gogameguru.com).

* **Upstream:** <https://github.com/gogameguru/go-problems>
* **License:** Creative Commons Attribution-NonCommercial-ShareAlike 4.0
  International (CC BY-NC-SA 4.0). Full text at `LICENSE.txt`.
* **Original README:** `README-upstream.md`

## What we use them for

`scripts/ingest_gogameguru.py` parses each SGF into a `DailyChallenge`
entry (board size, setup stones, side-to-move, difficulty from the
folder, topic assigned by deterministic split — see `topic_for()` in
that script). The output lives at
`backend/app/services/daily_challenge_gogameguru.py` and is imported
by `daily_challenge.py`.

## Attribution requirements (CC BY-NC-SA)

When the puzzles are surfaced to a user, the app credits the source
inline on the daily-challenge screen. The footer reads:

> 일부 문제는 GoGameGuru / An Younggil 8p / David Ormerod 의
> CC BY-NC-SA 4.0 라이선스 자료를 변형하여 사용했습니다.

## Commercial / non-commercial note

CC BY-NC-SA forbids primarily commercial use of the licensed material.
This app ships free, ad-free, and without in-app purchases. The
puzzles never gate paid features. If a future revision introduces
paid functionality, this catalogue must be removed before launch.

## Re-running the ingest

```bash
cd backend && python -m scripts.ingest_gogameguru
```

That regenerates `daily_challenge_gogameguru.py` from the vendored
SGFs and re-runs deterministically, so commit-checked outputs are
stable.

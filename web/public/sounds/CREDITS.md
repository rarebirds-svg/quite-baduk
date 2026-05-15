# Sound credits

| File | Source | License | Original author |
|---|---|---|---|
| stone-1.mp3 | ffmpeg lavfi anoisesrc + EQ chain (this repo, web/public/sounds/) | Public domain (algorithmic synthesis) | Regenerated 2026-05-11 — bright snappy click |
| stone-2.mp3 | ffmpeg lavfi anoisesrc + EQ chain (this repo, web/public/sounds/) | Public domain (algorithmic synthesis) | Regenerated 2026-05-11 — bright snappy click |
| stone-3.mp3 | ffmpeg lavfi anoisesrc + EQ chain (this repo, web/public/sounds/) | Public domain (algorithmic synthesis) | Regenerated 2026-05-11 — bright snappy click |

## Synthesis details

All three samples were regenerated 2026-05-11 with `ffmpeg` using white-noise sources
(`anoisesrc=color=white`) shaped into short, bright, snappy "딱" / "톡" clicks:

- 55–70 ms total duration with a 1 ms attack and a fast exponential-style fade-out (no tail)
- Highpass at 1.2–1.8 kHz removes muddy lows
- Parametric EQ peak at 2.8–4.2 kHz (+12 dB) carries the "click" presence ("맑고")
- Secondary EQ peak at 6.5–8.5 kHz (+5 dB) adds a sparkle highlight ("경쾌")
- Lowpass at 12–14 kHz to keep the top end clean
- Three variants differ slightly in spectral center and length so rapid clicks don't sound identical

No recorded audio was used. Each sample is under 100 ms and public domain.

Previous generation (2026-04-26 polish-pack) used brown/pink noise with a softer "stone-on-board
clack" character — replaced for a clearer, snappier feel.

Sabaki (https://github.com/SabakiHQ/Sabaki) was inspected as a potential source but does not
include a `resources/sounds/` directory in its current repository.

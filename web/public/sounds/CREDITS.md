# Sound credits

| File | Source | License | Original author |
|---|---|---|---|
| stone-1.mp3 | ffmpeg lavfi anoisesrc + EQ chain (this repo, web/public/sounds/) | Public domain (algorithmic synthesis) | Generated 2026-04-26 by polish-pack |
| stone-2.mp3 | ffmpeg lavfi anoisesrc + EQ chain (this repo, web/public/sounds/) | Public domain (algorithmic synthesis) | Generated 2026-04-26 by polish-pack |
| stone-3.mp3 | ffmpeg lavfi anoisesrc + EQ chain (this repo, web/public/sounds/) | Public domain (algorithmic synthesis) | Generated 2026-04-26 by polish-pack |

## Synthesis details

All three samples were generated with `ffmpeg` using brown/pink noise sources (`anoisesrc`),
filtered through a low-pass and parametric EQ chain to produce short percussive stone-on-board
clacks. No recorded audio was used. Each sample is under 150ms and public domain.

Sabaki (https://github.com/SabakiHQ/Sabaki) was inspected as a potential source but does not
include a `resources/sounds/` directory in its current repository.

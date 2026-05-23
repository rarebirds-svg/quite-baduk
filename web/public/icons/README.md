# Inkbaduk Icons

PNG icons for PWA·iOS·Android. Generated programmatically from
`backend/scripts/generate_brand_icons.py`. Re-run that script after any
brand visual change. Source colors come from `web/app/globals.css` —
paper `#F5EFE6`, ink `#1A1715`.

## Required files

| File | Size | Purpose |
|------|------|---------|
| `icon-192.png` | 192×192 | PWA manifest, Android home screen |
| `icon-512.png` | 512×512 | PWA manifest splash, Play Store |
| `icon-maskable-192.png` | 192×192 | Android adaptive icon (maskable) — keep art within the inner 66% safe zone |
| `icon-maskable-512.png` | 512×512 | Android adaptive icon large (maskable) — same safe-zone rule |
| `apple-touch-icon.png` | 180×180 | iOS Safari "Add to Home Screen" |
| `icon.svg` | scalable | 브라우저 탭 파비콘(모던) — 손으로 편집, 스크립트 미생성 |
| `../favicon.ico` | 16·32·48 | 브라우저 탭 파비콘(레거시) — `web/public/` 루트에 생성 |

## Design notes

- Background: `#F5EFE6` (light) — matches `--paper` CSS token in `globals.css`
- Maskable icons must keep all meaningful art inside the central 66% (132px of 192, 339px of 512)
  because Android crops to a circle/squircle using the outer 34% as bleed zone
- Apple touch icon: no rounded corners needed — iOS applies them automatically
- For a production-quality icon, consider a Go stone (black circle on paper background) or
  a simplified 3×3 grid motif in `--ink` (#1A1715) on `--paper` (#F5EFE6)

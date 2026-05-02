# Icon Placeholders — Replace Before App Store Submission

These PNG files are **solid-color placeholders** (#F5EFE6, the Editorial Hardcover paper background).
They are valid PNG files and will render a blank beige square. They must be replaced by the designer
before any App Store or Play Store submission.

## Required files

| File | Size | Purpose |
|------|------|---------|
| `icon-192.png` | 192×192 | PWA manifest, Android home screen |
| `icon-512.png` | 512×512 | PWA manifest splash, Play Store |
| `icon-maskable-192.png` | 192×192 | Android adaptive icon (maskable) — keep art within the inner 66% safe zone |
| `icon-maskable-512.png` | 512×512 | Android adaptive icon large (maskable) — same safe-zone rule |
| `apple-touch-icon.png` | 180×180 | iOS Safari "Add to Home Screen" |

## Design notes

- Background: `#F5EFE6` (light) — matches `--paper` CSS token in `globals.css`
- Maskable icons must keep all meaningful art inside the central 66% (132px of 192, 339px of 512)
  because Android crops to a circle/squircle using the outer 34% as bleed zone
- Apple touch icon: no rounded corners needed — iOS applies them automatically
- For a production-quality icon, consider a Go stone (black circle on paper background) or
  a simplified 3×3 grid motif in `--ink` (#1A1715) on `--paper` (#F5EFE6)

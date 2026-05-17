# Inkbaduk 브랜드 아이콘·OG 이미지 생성기.
# BrandMark SVG(한 줄과 교차하는 한 점)의 결을 PNG로 옮겨 PWA·iOS·OG에
# 일관 적용한다. Editorial Hardcover 색 토큰: paper #F5EFE6, ink #1A1715.
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent.parent
ICONS_DIR = REPO / "web" / "public" / "icons"
PUBLIC_DIR = REPO / "web" / "public"

PAPER = (245, 239, 230)  # #F5EFE6
INK = (26, 23, 21)       # #1A1715
INK_FAINT = (180, 175, 170)


def make_icon(size: int, *, maskable: bool = False) -> Image.Image:
    """Square icon. Standard variant has a thin grid line across; maskable
    keeps everything inside the inner 66% safe zone so Android adaptive
    crop doesn't slice the stone."""
    img = Image.new("RGB", (size, size), PAPER)
    draw = ImageDraw.Draw(img)

    if maskable:
        # Keep stone inside inner 66% safe zone. Smaller stone, no edge line.
        stone_r = int(size * 0.28)
        cx = cy = size // 2
        draw.ellipse(
            (cx - stone_r, cy - stone_r, cx + stone_r, cy + stone_r),
            fill=INK,
        )
        # Short line just within the safe zone — decorative, not edge-reaching.
        safe = int(size * 0.66)
        x0 = (size - safe) // 2
        x1 = x0 + safe
        line_w = max(2, int(size * 0.012))
        draw.line(((x0, cy), (x1, cy)), fill=INK, width=line_w)
    else:
        # Full-bleed variant: horizontal line edge to edge, stone in the center.
        stone_r = int(size * 0.35)
        cx = cy = size // 2
        line_w = max(2, int(size * 0.012))
        draw.line(((0, cy), (size, cy)), fill=INK, width=line_w)
        draw.ellipse(
            (cx - stone_r, cy - stone_r, cx + stone_r, cy + stone_r),
            fill=INK,
        )
    return img


def _font(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    """Load the first available font from a candidate list."""
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_og_image() -> Image.Image:
    """1200x630 Open Graph card. Serif wordmark + Hangul tagline +
    decorative stone-on-line mark to the right."""
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)

    serif = _font(
        [
            "/System/Library/Fonts/NewYork.ttf",
            "/System/Library/Fonts/Supplemental/Georgia.ttf",
            "/Library/Fonts/Georgia.ttf",
            "/System/Library/Fonts/Times.ttc",
        ],
        size=140,
    )
    hangul = _font(
        [
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
            "/Library/Fonts/AppleGothic.ttf",
            "/System/Library/Fonts/Supplemental/AppleMyungjo.ttf",
        ],
        size=44,
    )
    mono_small = _font(
        [
            "/System/Library/Fonts/SFNSMono.ttf",
            "/System/Library/Fonts/Monaco.ttf",
            "/System/Library/Fonts/Menlo.ttc",
        ],
        size=24,
    )

    margin = 80

    # Top-left tiny eyebrow
    draw.text(
        (margin, margin),
        "INKBADUK · VOL. I",
        fill=INK_FAINT,
        font=mono_small,
    )

    # Wordmark
    wordmark = "Inkbaduk"
    bbox = draw.textbbox((0, 0), wordmark, font=serif)
    wm_h = bbox[3] - bbox[1]
    wm_y = (H - wm_h) // 2 - 40
    draw.text((margin, wm_y), wordmark, fill=INK, font=serif)

    # Underline (rule divider) and tagline
    rule_y = wm_y + wm_h + 32
    draw.line(((margin, rule_y), (margin + 220, rule_y)), fill=INK, width=2)

    tagline_ko = "잉크바둑 · 조용한 승부"
    draw.text((margin, rule_y + 20), tagline_ko, fill=INK, font=hangul)

    # Decorative stone-on-line motif at the right, like the BrandMark
    motif_cx = W - 220
    motif_cy = H // 2
    motif_r = 80
    draw.line(((motif_cx - 280, motif_cy), (motif_cx + 160, motif_cy)), fill=INK, width=3)
    draw.ellipse(
        (motif_cx - motif_r, motif_cy - motif_r, motif_cx + motif_r, motif_cy + motif_r),
        fill=INK,
    )

    # Footer line
    footer = "KataGo Human-SL · 9k–9d · 18 styles"
    draw.text(
        (margin, H - margin - 24),
        footer,
        fill=INK_FAINT,
        font=mono_small,
    )

    return img


def main() -> None:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    targets: list[tuple[str, int, bool]] = [
        ("icon-192.png", 192, False),
        ("icon-512.png", 512, False),
        ("icon-maskable-192.png", 192, True),
        ("icon-maskable-512.png", 512, True),
        ("apple-touch-icon.png", 180, False),
    ]
    for name, size, maskable in targets:
        out = ICONS_DIR / name
        make_icon(size, maskable=maskable).save(out, "PNG", optimize=True)
        print(f"wrote {out} ({size}x{size}, maskable={maskable})")

    og = make_og_image()
    og_path = PUBLIC_DIR / "og-image.png"
    og.save(og_path, "PNG", optimize=True)
    print(f"wrote {og_path} (1200x630)")


if __name__ == "__main__":
    main()

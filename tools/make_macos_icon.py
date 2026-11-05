"""Build the macOS .icns icon from the Ling sprite sheet.

The standalone pet ships no vector artwork, so the icon is composed from the
first idle frame: a head-and-shoulders crop on a rounded cream tile, matching
the visual language of macOS Big Sur and later icon grids.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

CELL_WIDTH = 192
CELL_HEIGHT = 208
IDLE_HEAD_CROP = (40, 0, 152, 118)
CANVAS = 1024
TILE_INSET = 100
TILE_RADIUS = 185
TILE_COLOR = (247, 243, 234, 255)
SUBJECT_FILL = 0.62

ICONSET_SIZES = {
    "icon_16x16.png": 16,
    "icon_16x16@2x.png": 32,
    "icon_32x32.png": 32,
    "icon_32x32@2x.png": 64,
    "icon_128x128.png": 128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png": 256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png": 512,
    "icon_512x512@2x.png": 1024,
}


def rounded_tile() -> Image.Image:
    tile = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    mask = Image.new("L", (CANVAS, CANVAS), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (TILE_INSET, TILE_INSET, CANVAS - TILE_INSET - 1, CANVAS - TILE_INSET - 1),
        radius=TILE_RADIUS,
        fill=255,
    )
    tile.paste(Image.new("RGBA", (CANVAS, CANVAS), TILE_COLOR), (0, 0), mask)
    return tile


def compose_icon(sheet_path: Path) -> Image.Image:
    with Image.open(sheet_path) as source:
        sheet = source.convert("RGBA")
    if sheet.size != (CELL_WIDTH * 8, CELL_HEIGHT * 9):
        raise ValueError(f"Expected a {CELL_WIDTH * 8}x{CELL_HEIGHT * 9} sprite sheet, got {sheet.size}")
    head = sheet.crop(IDLE_HEAD_CROP)

    width, height = head.size
    scale = min(CANVAS * SUBJECT_FILL / width, CANVAS * SUBJECT_FILL / height)
    head = head.resize((round(width * scale), round(height * scale)), Image.LANCZOS)

    icon = rounded_tile()
    icon.alpha_composite(head, ((CANVAS - head.width) // 2, (CANVAS - head.height) // 2))
    return icon


def write_icns(icon: Image.Image, output: Path) -> None:
    iconutil = shutil.which("iconutil")
    if iconutil is None:
        raise RuntimeError("iconutil was not found; install the Xcode command line tools")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "Ling.iconset"
        iconset.mkdir()
        for filename, size in ICONSET_SIZES.items():
            icon.resize((size, size), Image.LANCZOS).save(iconset / filename)
        subprocess.run([iconutil, "-c", "icns", str(iconset), "-o", str(output)], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", type=Path, default=Path("pet/ling/spritesheet.webp"))
    parser.add_argument("--output", type=Path, default=Path("build/Ling.icns"))
    parser.add_argument("--preview", type=Path, help="also write a 1024px PNG preview")
    args = parser.parse_args()

    icon = compose_icon(args.sheet)
    write_icns(icon, args.output)
    if args.preview:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        icon.save(args.preview)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

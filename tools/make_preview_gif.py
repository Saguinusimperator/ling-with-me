"""Rebuild docs/assets/preview.gif from the 2x atlases, one column per outfit.

The GIF cycles the same six actions for every skin so the outfits can be
compared side by side: idle, waving, jumping, running, review, failed.
Frame order and counts must stay in sync with ANIMATIONS in ling_app.py.
"""
import argparse
from pathlib import Path

from PIL import Image

CELL_W, CELL_H = 384, 416
SCALE = 2
BACKGROUND = (242, 238, 235)
SEQUENCE = [  # (row, frame count) in atlas order
    (0, 6),   # idle
    (3, 4),   # waving
    (4, 5),   # jumping
    (7, 6),   # running
    (8, 6),   # review
    (5, 8),   # failed
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skins", nargs="+", default=["ling", "ling-heart", "ling-feather"])
    parser.add_argument("--output", type=Path, default=Path("docs/assets/preview.gif"))
    parser.add_argument("--duration", type=int, default=150)
    parser.add_argument("--colors", type=int, default=128)
    args = parser.parse_args()

    sheets = {}
    for skin in args.skins:
        path = Path("pet") / skin / "spritesheet@2x.webp"
        sheets[skin] = Image.open(path).convert("RGBA")

    width = CELL_W * len(args.skins)
    frames = []
    for row, count in SEQUENCE:
        for col in range(count):
            frame = Image.new("RGBA", (width, CELL_H), BACKGROUND + (255,))
            for index, skin in enumerate(args.skins):
                cell = sheets[skin].crop(
                    (col * CELL_W, row * CELL_H, (col + 1) * CELL_W, (row + 1) * CELL_H)
                )
                frame.alpha_composite(cell, (index * CELL_W, 0))
            frames.append(frame.convert("RGB"))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    palette_frames = [frame.quantize(colors=args.colors) for frame in frames]
    palette_frames[0].save(
        args.output,
        save_all=True,
        append_images=palette_frames[1:],
        duration=args.duration,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"wrote {args.output} {frames[0].size} {len(frames)} frames "
          f"({args.output.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()

"""Register generated 4x2 hanging atlases to two stable grip anchors.

Usage: python tools/pack_hanging.py SILVER_ATLAS HEART_ATLAS
Only slices, registers and resizes AI-generated sprites for runtime consumption.
"""
import json
from pathlib import Path
import shutil
import sys

from PIL import Image


def pack(source_path, skin, root):
    source = Image.open(source_path).convert("RGBA")
    strip = Image.new("RGBA", (192 * 8, 208))
    registration = []
    for index in range(8):
        column, row = index % 4, index // 4
        cell = source.crop((round(column * source.width / 4), row * source.height // 2,
                            round((column + 1) * source.width / 4), (row + 1) * source.height // 2))
        alpha = cell.getchannel("A").point(lambda v: 255 if v > 128 else 0)
        bounds = alpha.getbbox()
        if bounds is None:
            raise ValueError("Empty hanging frame")
        top = bounds[1]
        # Both fists are the highest features in these generated atlases.
        band = alpha.crop((0, top + 3, cell.width, top + 22))
        split = cell.width // 2
        left = band.crop((0, 0, split, band.height)).getbbox()
        right = band.crop((split, 0, band.width, band.height)).getbbox()
        if left is None or right is None:
            raise ValueError("Could not locate both grip anchors")
        grip_left = (left[0] + left[2]) / 2
        grip_right = split + (right[0] + right[2]) / 2
        scale_y = 0.46
        scale_x = scale_y if skin == "ling-heart" else 44 / (grip_right - grip_left)
        runtime_half_span = (grip_right - grip_left) * scale_x / 2
        runtime_left, runtime_right = 96 - runtime_half_span, 96 + runtime_half_span
        grip_y = top + 14
        # Preserve the heart outfit's aspect ratio; align the grip midpoint
        # instead of widening its naturally narrower hand spacing.
        frame = cell.transform((192, 208), Image.Transform.AFFINE,
                               (1 / scale_x, 0, grip_left - runtime_left / scale_x,
                                0, 1 / scale_y, grip_y - 10 / scale_y),
                               resample=Image.Resampling.BICUBIC)
        strip.alpha_composite(frame, (index * 192, 0))
        registration.append({"frame": index, "source_grips": [[grip_left, grip_y], [grip_right, grip_y]],
                             "runtime_grips": [[runtime_left, 10], [runtime_right, 10]],
                             "scale": [scale_x, scale_y]})
    strip.save(root / "pet" / skin / "hang.png")
    return registration


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    out = root / "build" / "hanging-qa"
    (out / "source").mkdir(parents=True, exist_ok=True)
    report = {}
    for skin, source in zip(("ling", "ling-heart"), sys.argv[1:], strict=True):
        shutil.copy2(source, out / "source" / f"{skin}.png")
        report[skin] = pack(source, skin, root)
    (out / "registration.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

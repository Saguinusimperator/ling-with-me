"""Rebuild the standalone sprite assets at 2x from the original imagegen strips.

The repository only ships the finished 192x208 cells. The original strips live
outside the repository (see docs/MACOS.md); this tool keys them, registers each
frame against the shipped 1x cell, and resamples at 2x so the Retina build keeps
the exact same geometry with real detail instead of an upscaled 1x image.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

CELL_W, CELL_H = 192, 208
SCALE = 2
OUT_W, OUT_H = CELL_W * SCALE, CELL_H * SCALE
SHEET_COLS = 8
SHEET_ROWS = 9
BLUE = (0, 2, 252)
KEY_LOW, KEY_HIGH = 96.0, 160.0
DESPILL = 12.0
PAD = 96

ANIMATIONS = {
    "idle": (0, 6),
    "right": (1, 8),
    "left": (2, 8),
    "waving": (3, 4),
    "jumping": (4, 5),
    "failed": (5, 8),
    "waiting": (6, 6),
    "running": (7, 6),
    "review": (8, 6),
}
SOURCE_ROWS = {
    "idle": "idle",
    "right": "running-right",
    "left": "running-left",
    "waving": "waving",
    "jumping": "jumping",
    "failed": "failed",
    "waiting": "waiting",
    "running": "running",
    "review": "review",
}
SKINS = {
    "ling": {
        "root": "ling-pet-run",
        "perch": "ling-with-me/build/perch-qa/source/ling.png",
        "hang": "ling-with-me/build/hanging-qa/source/ling.png",
        "hang_grid": (4, 2),
    },
    "ling-heart": {
        "root": "versions/ling-heart",
        "perch": "ling-with-me/build/perch-qa/source/ling-heart.png",
        "hang": "ling-with-me/build/hanging-qa/source/ling-heart.png",
        "hang_grid": (4, 2),
    },
}


def chroma_key(cell: Image.Image) -> Image.Image:
    """Return RGBA with the blue backdrop removed and edge spill undone."""
    arr = np.asarray(cell.convert("RGB")).astype(np.float32)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    blueness = b - np.maximum(r, g)

    # Despill first: anti-aliased dark outlines pick up a blue cast that would
    # otherwise survive as a coloured rim around the character.
    arr[..., 2] = np.where(blueness > DESPILL, np.maximum(r, g), b)

    alpha = np.clip((KEY_HIGH - blueness) / (KEY_HIGH - KEY_LOW), 0.0, 1.0)
    alpha = np.where(blueness <= KEY_LOW, 1.0, alpha)
    alpha = np.where(blueness >= KEY_HIGH, 0.0, alpha)

    # C = a*F + (1-a)*blue  ->  F = (C - (1-a)*blue) / a
    a = alpha[..., None]
    with np.errstate(divide="ignore", invalid="ignore"):
        fg = (arr - (1.0 - a) * np.array(BLUE, dtype=np.float32)) / a
    fg = np.where(a > 0.02, fg, 0.0)
    rgba = np.concatenate([np.clip(fg, 0, 255), alpha[..., None] * 255.0], axis=2)
    return Image.fromarray(rgba.round().astype(np.uint8), "RGBA")


def alpha_mask(img: Image.Image, threshold: int = 8) -> np.ndarray:
    return np.asarray(img.getchannel("A")) > threshold


def remove_specks(img: Image.Image, min_ratio: float = 0.002, floor: int = 24) -> Image.Image:
    """Drop stray generation marks that the tiny 1x cells hid anyway."""
    arr = np.asarray(img).copy()
    mask = arr[..., 3] > 8
    labels, count = ndimage.label(mask)
    if count <= 1:
        return img
    sizes = ndimage.sum(mask, labels, range(1, count + 1))
    keep = {i + 1 for i, size in enumerate(sizes) if size >= max(floor, sizes.max() * min_ratio)}
    if len(keep) == count:
        return img
    drop = ~np.isin(labels, list(keep))
    arr[drop] = 0
    return Image.fromarray(arr, "RGBA")


def _correlate(source: np.ndarray, template: np.ndarray):
    """Valid-mode cross correlation plus normalised overlap for every offset."""
    sh, sw = source.shape
    th, tw = template.shape
    if th > sh or tw > sw:
        return None
    size = (1 << (sh + th - 1).bit_length(), 1 << (sw + tw - 1).bit_length())
    fa = np.fft.rfft2(source.astype(np.float32), size)
    fb = np.fft.rfft2(template[::-1, ::-1].astype(np.float32), size)
    conv = np.fft.irfft2(fa * fb, size)[th - 1 : th - 1 + sh - th + 1, tw - 1 : tw - 1 + sw - tw + 1]
    conv = np.clip(conv, 0, None)

    integral = np.pad(source.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    dy, dx = np.mgrid[0 : sh - th + 1, 0 : sw - tw + 1]
    window = (
        integral[dy + th, dx + tw] - integral[dy, dx + tw] - integral[dy + th, dx] + integral[dy, dx]
    )
    union = window + template.sum() - conv
    score = np.where(union > 0, conv / np.maximum(union, 1), 0.0)
    return score


def register(one_x: np.ndarray, source: np.ndarray, guess: float, spans=(0.06, 0.02, 0.007)) -> tuple[float, float, float, float]:
    """Find the scale and cell offset that map the 1x character onto the strip.

    The template is the character's bounding box inside the 1x cell, not the
    whole cell: the shipped cell carries transparent margins that do not exist
    in the tightly cropped source strip. The source is padded so that a
    character touching the strip edge can still be matched.
    """
    ys, xs = np.nonzero(one_x)
    if not len(xs):
        return guess, 0.0, 0.0, -1.0
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    character = one_x[y0:y1, x0:x1]
    padded = np.pad(source, PAD)
    best = (guess, 0.0 - x0 * guess, 0.0 - y0 * guess, -1.0)

    for span in spans:
        around = best[0]
        for s in np.linspace(around * (1 - span), around * (1 + span), 9):
            w, h = max(1, round((x1 - x0) * s)), max(1, round((y1 - y0) * s))
            if w > padded.shape[1] or h > padded.shape[0]:
                continue
            template = np.asarray(
                Image.fromarray((character * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
            ) > 127
            score = _correlate(padded, template)
            if score is None:
                continue
            idx = int(np.argmax(score))
            value = float(score.flat[idx])
            if value > best[3]:
                dy, dx = np.unravel_index(idx, score.shape)
                # Convert the padded character offset back to the cell's top-left.
                best = (float(s), float(dx - PAD) - x0 * s, float(dy - PAD) - y0 * s, value)
    return best


def render(source: Image.Image, s: float, dx: float, dy: float) -> Image.Image:
    """Sample the source so output pixel (X, Y) maps to (dx + X*s/2, dy + Y*s/2)."""
    arr = np.asarray(source).astype(np.float32)
    alpha = arr[..., 3:4] / 255.0
    premultiplied = arr.copy()
    premultiplied[..., :3] *= alpha
    prem = Image.fromarray(premultiplied.round().astype(np.uint8), "RGBA")
    matrix = (s / SCALE, 0.0, float(dx), 0.0, s / SCALE, float(dy))
    out = np.asarray(
        prem.transform((OUT_W, OUT_H), Image.Transform.AFFINE, matrix, resample=Image.BICUBIC)
    ).astype(np.float32)
    a = out[..., 3:4] / 255.0
    with np.errstate(divide="ignore", invalid="ignore"):
        rgb = np.where(a > 0.004, out[..., :3] / np.maximum(a, 1e-4), 0.0)
    rgba = np.concatenate([np.clip(rgb, 0, 255), out[..., 3:4]], axis=2)
    return Image.fromarray(rgba.round().astype(np.uint8), "RGBA")


def iou(a: Image.Image, b: Image.Image) -> float:
    ma, mb = alpha_mask(a), alpha_mask(b)
    inter = np.logical_and(ma, mb).sum()
    union = np.logical_or(ma, mb).sum()
    return float(inter / union) if union else 1.0


def load_one_x_cell(sheet: Image.Image, row: int, col: int) -> Image.Image:
    return sheet.crop((col * CELL_W, row * CELL_H, (col + 1) * CELL_W, (row + 1) * CELL_H))


def strip_cells(img: Image.Image, count: int, rows: int = 1) -> list[Image.Image]:
    w, h = img.width / count, img.height / rows
    return [
        img.crop((round(c * w), round(r * h), round((c + 1) * w), round((r + 1) * h)))
        for r in range(rows)
        for c in range(count)
    ]


def clear_border(img: Image.Image, width: int = 4) -> Image.Image:
    """Zero the outermost pixels; generation strips often carry edge specks."""
    arr = np.asarray(img).copy()
    arr[:width, :, 3] = 0
    arr[-width:, :, 3] = 0
    arr[:, :width, 3] = 0
    arr[:, -width:, 3] = 0
    return Image.fromarray(arr, "RGBA")


def build_strip(source_cells: list[Image.Image], target_cells: list[Image.Image], label: str,
                guess_by_width: bool = False, fixed_guess: float | None = None, wide: bool = False):
    out, report = [], []
    for index, (src, target) in enumerate(zip(source_cells, target_cells)):
        a1, asrc = alpha_mask(target), alpha_mask(src)
        bbox1, bboxs = target.getbbox(), src.getbbox()
        if not bbox1 or not bboxs:
            raise RuntimeError(f"{label} frame {index}: empty cell")
        if fixed_guess:
            guess = fixed_guess
            spans = (0.08, 0.02, 0.007)
        elif guess_by_width:
            guess = (bboxs[2] - bboxs[0]) / (bbox1[2] - bbox1[0])
            spans = (0.12, 0.03, 0.01)
        else:
            guess = (bboxs[3] - bboxs[1]) / (bbox1[3] - bbox1[1])
            spans = (0.12, 0.03, 0.01) if wide else (0.06, 0.02, 0.007)
        s, dx, dy, score = register(a1, asrc, guess, spans)
        frame = render(src, s, dx, dy)
        back = frame.resize((CELL_W, CELL_H), Image.LANCZOS)
        out.append(frame)
        report.append(
            {
                "frame": index,
                "scale": round(float(s), 4),
                "offset": [round(float(dx), 2), round(float(dy), 2)],
                "match": round(float(score), 4),
                "iou_1x": round(float(iou(back, target)), 4),
            }
        )
        print(f"  {label} {index}: s={s:.3f} offset=({dx:.1f},{dy:.1f}) match={score:.3f} iou={report[-1]['iou_1x']:.3f}")
    return out, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--skin", choices=sorted(SKINS), action="append")
    parser.add_argument("--skip-perch", action="store_true")
    parser.add_argument("--only", choices=("sheet", "perch", "hang"), action="append")
    parser.add_argument("--qa", type=Path, default=Path("build/retina-qa"))
    args = parser.parse_args()

    skins = args.skin or sorted(SKINS)
    kinds = set(args.only or ("sheet", "perch", "hang"))
    args.qa.mkdir(parents=True, exist_ok=True)
    summary = {}

    for skin in skins:
        config = SKINS[skin]
        root = args.source_root / config["root"]
        sheet_1x = Image.open(args.repo / "pet" / skin / "spritesheet.webp").convert("RGBA")
        canvas = Image.new("RGBA", (SHEET_COLS * OUT_W, SHEET_ROWS * OUT_H), (0, 0, 0, 0))
        report = {}

        if "sheet" in kinds:
            for state, (row, count) in ANIMATIONS.items():
                src_path = root / "decoded" / f"{SOURCE_ROWS[state]}.png"
                strip = Image.open(src_path).convert("RGB")
                source_cells = [remove_specks(chroma_key(c)) for c in strip_cells(strip, count)]
                target_cells = [load_one_x_cell(sheet_1x, row, col) for col in range(count)]
                frames, rows_report = build_strip(source_cells, target_cells, f"{skin}/{state}")
                for col, frame in enumerate(frames):
                    canvas.alpha_composite(frame, (col * OUT_W, row * OUT_H))
                report[state] = rows_report

            sheet_out = args.repo / "pet" / skin / "spritesheet@2x.webp"
            canvas.save(sheet_out, lossless=True, method=6, quality=100)
            print(f"wrote {sheet_out} ({sheet_out.stat().st_size / 1e6:.2f} MB)")

        if not args.skip_perch:
            for kind, cols, rows, filename in (
                ("perch", 6, 1, "perch"),
                ("hang", 4, 2, "hang"),
            ):
                if kind not in kinds:
                    continue
                count = cols * rows
                src_img = Image.open(args.source_root / config[kind]).convert("RGBA")
                target_img = Image.open(args.repo / "pet" / skin / f"{filename}.png").convert("RGBA")
                src_cells = strip_cells(src_img, cols, rows)
                if kind == "hang":
                    # Hanging cells are cropped from a 0.46-scaled atlas, so a
                    # bbox ratio is meaningless; the scale is fixed.
                    src_cells = [clear_border(c) for c in src_cells]
                else:
                    src_cells = [remove_specks(c) for c in src_cells]
                tgt_cells = strip_cells(target_img, count, 1)
                frames, rows_report = build_strip(
                    src_cells, tgt_cells, f"{skin}/{kind}",
                    wide=(kind == "perch"),
                    fixed_guess=2.15 if kind == "hang" else None,
                )
                out_img = Image.new("RGBA", (count * OUT_W, OUT_H), (0, 0, 0, 0))
                for i, frame in enumerate(frames):
                    out_img.alpha_composite(frame, (i * OUT_W, 0))
                out_path = args.repo / "pet" / skin / f"{filename}@2x.png"
                out_img.save(out_path)
                print(f"wrote {out_path} ({out_path.stat().st_size / 1e6:.2f} MB)")
                report[kind] = rows_report

        summary[skin] = report

    (args.qa / "registration.json").write_text(json.dumps(summary, indent=2))
    low = [
        (skin, kind, item["frame"], item["iou_1x"], item["match"])
        for skin, report in summary.items()
        for kind, rows in report.items()
        for item in rows
        if item["iou_1x"] < 0.97
    ]
    print(f"\nframes below 0.97 IoU: {len(low)}")
    for row in low:
        print("  ", row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

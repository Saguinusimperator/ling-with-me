"""Match facial skin tone across the two fixed 8x9 Ling sprite atlases.

Only pixels in the upper face area that match the existing skin palette are
changed. The idle row is the color reference for each outfit.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
CELL_WIDTH = 192
CELL_HEIGHT = 208
REFERENCE = {"ling": (253, 223, 196), "ling-heart": (252, 218, 186)}


def skin_mask(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    red = rgb[:, :, 0].astype(float)
    green = rgb[:, :, 1].astype(float)
    blue = rgb[:, :, 2].astype(float)
    red_safe = np.maximum(red, 1)
    return (
        (alpha > 230) & (red > 180)
        & (green / red_safe > 0.77) & (green / red_safe < 0.94)
        & (blue / red_safe > 0.66) & (blue / red_safe < 0.90)
        & (green - blue > 10) & (green - blue < 42)
        & (red - green < 55)
    )


def correct(skin: str) -> None:
    path = ROOT / "pet" / skin / "spritesheet.webp"
    with Image.open(path) as source:
        pixels = np.asarray(source.convert("RGBA")).copy()
    if pixels.shape != (9 * CELL_HEIGHT, 8 * CELL_WIDTH, 4):
        raise ValueError(f"Unexpected atlas dimensions: {path}")
    original_alpha = pixels[:, :, 3].copy()
    target = np.array(REFERENCE[skin], dtype=float)
    for row in range(1, 9):
        y0 = row * CELL_HEIGHT
        face_area = pixels[y0:y0 + 105]
        mask = skin_mask(face_area[:, :, :3], face_area[:, :, 3])
        if mask.sum() < 1000:
            raise ValueError(f"Insufficient face pixels: {skin} row {row}")
        median = np.median(face_area[:, :, :3][mask], axis=0)
        delta = target - median
        if np.max(np.abs(delta)) < 1:
            continue
        for col in range(8):
            x0 = col * CELL_WIDTH
            cell = pixels[y0:y0 + 105, x0:x0 + CELL_WIDTH]
            selected = skin_mask(cell[:, :, :3], cell[:, :, 3])
            soft = Image.fromarray((selected * 255).astype("uint8"), "L")
            soft = soft.filter(ImageFilter.GaussianBlur(1.0))
            weight = np.asarray(soft, dtype=float)[:, :, None] / 255
            adjusted = np.clip(cell[:, :, :3].astype(float) + weight * delta, 0, 255)
            cell[:, :, :3] = np.rint(adjusted).astype("uint8")
        print(f"{skin} row {row}: median {median.astype(int)} -> target {target.astype(int)}")
    if not np.array_equal(original_alpha, pixels[:, :, 3]):
        raise AssertionError("Transparency changed")
    pixels[pixels[:, :, 3] == 0, :3] = 0
    Image.fromarray(pixels, "RGBA").save(path, "WEBP", lossless=True, method=6, exact=True)


def correct_strip(skin: str, filename: str, count: int, bounds: tuple[int, int, int, int]) -> None:
    path = ROOT / "pet" / skin / filename
    with Image.open(path) as source:
        pixels = np.asarray(source.convert("RGBA")).copy()
    if pixels.shape != (CELL_HEIGHT, count * CELL_WIDTH, 4):
        raise ValueError(f"Unexpected strip dimensions: {path}")
    x1, y1, x2, y2 = bounds
    samples = []
    for col in range(count):
        cell = pixels[y1:y2, col * CELL_WIDTH + x1:col * CELL_WIDTH + x2]
        selected = skin_mask(cell[:, :, :3], cell[:, :, 3])
        samples.extend(cell[:, :, :3][selected])
    if len(samples) < 500:
        raise ValueError(f"Insufficient face pixels: {path}")
    median = np.median(np.asarray(samples), axis=0)
    delta = np.array(REFERENCE[skin], dtype=float) - median
    for col in range(count):
        cell = pixels[y1:y2, col * CELL_WIDTH + x1:col * CELL_WIDTH + x2]
        selected = skin_mask(cell[:, :, :3], cell[:, :, 3])
        soft = Image.fromarray((selected * 255).astype("uint8"), "L")
        weight = np.asarray(soft.filter(ImageFilter.GaussianBlur(1.0)), dtype=float)[:, :, None] / 255
        cell[:, :, :3] = np.rint(np.clip(cell[:, :, :3].astype(float) + weight * delta, 0, 255)).astype("uint8")
    Image.fromarray(pixels, "RGBA").save(path)
    print(f"{skin} {filename}: median {median.astype(int)} -> target {REFERENCE[skin]}")


if __name__ == "__main__":
    for variant in REFERENCE:
        correct(variant)
        correct_strip(variant, "perch.png", 6, (20, 105, 105, 180))
        correct_strip(variant, "hang.png", 8, (40, 30, 145, 105))

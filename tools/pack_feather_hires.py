"""Pack independently generated feather actions without enlarging source pixels.

Only spritesheet(.@2x).webp is replaced; perch/hang and other skins are untouched.
Inputs are pure-blue action grids named after ANIMATIONS. Source grids, prompts
and the JSON report stay in the ignored private workspace.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from PIL import Image

from build_retina_assets import ANIMATIONS, chroma_key, clear_border, remove_specks, render


GRIDS = {
    'idle': (3, 2), 'right': (4, 2), 'left': (4, 2),
    'waving': (2, 2), 'jumping': (3, 2), 'failed': (4, 2),
    'waiting': (3, 2), 'running': (3, 2), 'review': (3, 2),
}


def load_cells(path: Path, state: str) -> list[Image.Image]:
    cols, rows = GRIDS[state]
    count = ANIMATIONS[state][1]
    with Image.open(path) as source:
        width, height = source.size
        if width // cols < 384 or height // rows < 416:
            raise ValueError(f'{state}: native cells must be at least 384x416; '
                             f'got {width / cols:.1f}x{height / rows:.1f}')
        cells = []
        for index in range(count):
            col, row = index % cols, index // cols
            box = (round(col * width / cols), round(row * height / rows),
                   round((col + 1) * width / cols), round((row + 1) * height / rows))
            # Some generators draw a 1px separator despite the no-grid prompt.
            # Drop only the outer 3px of the blue margin, then still reject art
            # within 4px of the edge rather than silently cropping a character.
            cell = remove_specks(clear_border(chroma_key(source.crop(box)), width=3))
            solid = cell.getchannel('A').point(lambda v: 255 if v > 128 else 0)
            bounds = solid.getbbox()
            if bounds is None:
                raise ValueError(f'{state}/{index}: empty source frame')
            x0, y0, x1, y1 = bounds
            if x0 <= 4 or y0 <= 4 or x1 >= cell.width - 4 or y1 >= cell.height - 4:
                raise ValueError(f'{state}/{index}: artwork touches cell border: {bounds}')
            cells.append(cell)
    return cells


def pack(source_root: Path, output: Path, report_path: Path) -> dict:
    sheet_2x = Image.new('RGBA', (3072, 3744))
    sheet_1x = Image.new('RGBA', (1536, 1872))
    report = {'policy': 'native cells >=384x416; no enlargement; no sharpening',
              'actions': {}}
    for state, (row, count) in ANIMATIONS.items():
        path = source_root / f'{state}.png'
        cells = load_cells(path, state)
        boxes = [cell.getchannel('A').point(lambda v: 255 if v > 128 else 0).getbbox()
                 for cell in cells]
        # A single scale per action preserves the head/body size across poses.
        # Jump frames share their source baseline, preserving airborne height.
        height = max(b[3] - b[1] for b in boxes)
        width = max(b[2] - b[0] for b in boxes)
        if state == 'jumping':
            # Fit the entire trajectory, not only the tallest individual pose.
            height = max(b[3] for b in boxes) - min(b[1] for b in boxes)
        scale = min(368 / height, 320 / width)
        if scale > 1:
            raise ValueError(f'{state}: character is too small in its native cell '
                             f'({width}x{height}); would need {scale:.3f}x enlargement')
        baseline = max(b[3] for b in boxes)
        action_report = {'source': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'native_cell_sizes': [list(cell.size) for cell in cells],
                         'scale_to_2x': scale, 'frames': []}
        for column, (cell, box) in enumerate(zip(cells, boxes)):
            dx = 192 - (box[0] + box[2]) * scale / 2
            dy = 400 - (baseline if state == 'jumping' else box[3]) * scale
            # render() uses premultiplied RGBA: no coloured interpolation fringes.
            frame = render(cell, 2 / scale, -dx / scale, -dy / scale)
            bounds = frame.getbbox()
            if bounds is None or bounds[0] <= 0 or bounds[1] <= 0 or bounds[2] >= 384 or bounds[3] >= 416:
                raise ValueError(f'{state}/{column}: output clipping: {bounds}')
            sheet_2x.alpha_composite(frame, (384 * column, 416 * row))
            # Derive 1x directly from the same rendered geometry, with no unsharp mask.
            small = frame.resize((192, 208), Image.Resampling.LANCZOS)
            sheet_1x.alpha_composite(small, (192 * column, 208 * row))
            action_report['frames'].append({'frame': column, 'source_bbox': box, 'output_bbox': bounds})
        assert len(action_report['frames']) == count
        report['actions'][state] = action_report

    output.mkdir(parents=True, exist_ok=True)
    # Validate all nine actions before replacing either runtime file.
    with tempfile.TemporaryDirectory(prefix='feather-pack-', dir=output) as temp:
        for name, sheet in [('spritesheet.webp', sheet_1x), ('spritesheet@2x.webp', sheet_2x)]:
            path = Path(temp) / name
            sheet.save(path, lossless=True, quality=100, method=6)
        for name in ['spritesheet.webp', 'spritesheet@2x.webp']:
            (Path(temp) / name).replace(output / name)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=root / 'pet/ling-feather')
    parser.add_argument('--report', type=Path, default=root / 'private/work/ling-feather/qa/hires-v2.json')
    args = parser.parse_args()
    report = pack(args.source_root, args.output, args.report)
    for state, action in report['actions'].items():
        print(f'{state}: {len(action["frames"])} frames, {action["scale_to_2x"]:.3f}x native scale')


if __name__ == '__main__':
    main()

"""Guard against low-res sources and clipping the peak of a jump trajectory."""
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent / 'tools'))
from pack_feather_hires import ANIMATIONS, GRIDS, load_cells, pack


class FeatherSourceTests(unittest.TestCase):
    def test_rejects_small_native_cells(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'idle.png'
            Image.new('RGB', (768, 512), '#0002fc').save(path)
            with self.assertRaisesRegex(ValueError, 'native cells'):
                load_cells(path, 'idle')

    def test_rejects_character_cut_off_at_cell_border(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'idle.png'
            image = Image.new('RGB', (1536, 1024), '#0002fc')
            ImageDraw.Draw(image).rectangle((0, 50, 250, 480), fill='white')
            image.save(path)
            with self.assertRaisesRegex(ValueError, 'touches cell border'):
                load_cells(path, 'idle')

    def test_full_jump_trajectory_fits_and_attachments_are_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources = root / 'sources'
            sources.mkdir()
            output = root / 'pet'
            output.mkdir()
            sentinel = output / 'hang.png'
            sentinel.write_bytes(b'attachment must not be regenerated')
            for state, (_, count) in ANIMATIONS.items():
                cols, rows = GRIDS[state]
                image = Image.new('RGB', (512 * cols, 512 * rows), '#0002fc')
                draw = ImageDraw.Draw(image)
                for index in range(count):
                    x, y = 512 * (index % cols), 512 * (index // cols)
                    # Airborne frame has a higher top AND higher feet; fitting
                    # only the tallest pose used to clip the jump's peak.
                    if state == 'jumping':
                        box = (130, 20, 380, 370) if index == 2 else (130, 120, 380, 485)
                    else:
                        box = (130, 80, 380, 485)
                    draw.rectangle((x + box[0], y + box[1], x + box[2], y + box[3]), fill='white')
                image.save(sources / f'{state}.png')
            report = pack(sources, output, root / 'report.json')
            self.assertEqual(sentinel.read_bytes(), b'attachment must not be regenerated')
            self.assertEqual(sum(len(a['frames']) for a in report['actions'].values()), 57)
            for name, size in [('spritesheet.webp', (1536, 1872)), ('spritesheet@2x.webp', (3072, 3744))]:
                with Image.open(output / name) as image:
                    self.assertEqual(image.size, size)
            for frame in report['actions']['jumping']['frames']:
                self.assertGreater(frame['output_bbox'][1], 0)
                self.assertLess(frame['output_bbox'][3], 416)
            for action in report['actions'].values():
                self.assertLessEqual(action['scale_to_2x'], 1)


if __name__ == '__main__':
    unittest.main()

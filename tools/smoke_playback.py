"""Record real-time Qt playback for both outfits with isolated settings.

Captures the running pet widgets on a neutral canvas, without desktop content.
Requires ffmpeg on PATH. Output is under build/playback-qa/.
"""
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ling_app as ling
from PySide6.QtGui import QColor, QFont, QImage, QPainter


def main():
    app = ling.QApplication([])
    out = Path('build/playback-qa')
    out.mkdir(parents=True, exist_ok=True)
    pets = []
    observations = {}
    labels = dict(zip(ling.ANIMATIONS, ('Idle', 'Walk right', 'Walk left', 'Wave', 'Jump', 'Sad', 'Wait', 'Busy', 'Review')))
    with tempfile.TemporaryDirectory(prefix='ling-playback-') as tmp:
        frames = {skin: ling.load_frames(ling.sheet_path(skin)) for skin in ling.SKINS}
        for i, skin in enumerate(ling.SKINS):
            with patch.object(ling, 'settings_path', return_value=Path(tmp) / f'{skin}.ini'):
                pet = ling.LingWindow(frames, skin)
            pet.rng = random.Random(12 + i)
            pet.animation_queue.clear()
            pet.start_next_auto()
            # This fixture observes uninterrupted automatic playback.
            pet.refresh_hover = lambda: None
            pet.show()
            pets.append(pet)
            observations[skin] = []
        start_x = [p.x() for p in pets]
        start = time.monotonic()
        frame_number = 0
        try:
            while time.monotonic() - start < 30:
                app.processEvents()
                elapsed = time.monotonic() - start
                for p in pets:
                    rows = observations[p.skin_id]
                    if not rows or rows[-1]['state'] != p.state:
                        rows.append({'seconds': round(elapsed, 3), 'state': p.state})
                if elapsed >= frame_number / 10:
                    image = QImage(max(800, len(pets) * 300), 400, QImage.Format.Format_RGB32)
                    image.fill(QColor('#f6f8fb'))
                    painter = QPainter(image)
                    painter.setFont(QFont('Segoe UI', 15))
                    painter.setPen(QColor('#243447'))
                    painter.drawText(24, 34, 'Ling | real-time widget capture | 1.6 s per cycle')
                    for i, p in enumerate(pets):
                        x = 45 + i * 300
                        painter.setFont(QFont('Segoe UI', 12))
                        painter.drawText(x, 83, p.skin_id)
                        painter.drawText(x, 110, labels[p.state])
                        painter.drawPixmap(x + p.x() - start_x[i], 140, p.grab())
                    painter.end()
                    image.save(str(out / f'frame-{frame_number:04d}.png'))
                    frame_number += 1
                time.sleep(0.003)
            for skin, rows in observations.items():
                assert set(row['state'] for row in rows[:9]) == set(ling.ANIMATIONS), (skin, rows)
                for a, b in zip(rows[:8], rows[1:9]):
                    assert abs(b['seconds'] - a['seconds'] - 3.2) < 0.18, (skin, a, b)
            (out / 'timing.json').write_text(json.dumps(observations, indent=2), encoding='utf-8')
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '10', '-i', str(out / 'frame-%04d.png'), '-frames:v', str(frame_number), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out / 'Ling-playback.mp4')], check=True)
            print(json.dumps({'video': str((out / 'Ling-playback.mp4').resolve()), 'frames': frame_number, 'timing': observations}, indent=2))
        finally:
            for p in pets:
                p.close()


if __name__ == '__main__':
    main()

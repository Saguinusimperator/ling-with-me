"""Standalone Windows desktop companion for Ling."""

from __future__ import annotations

import io
import os
import random
import sys
import time
from pathlib import Path

from PIL import Image

if sys.platform == "win32":
    # Other desktop tools may put an incompatible ICU DLL on PATH. Load the
    # Windows copy before Qt so its unversioned ICU entry points resolve.
    import ctypes

    ctypes.WinDLL(str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "icuuc.dll"))

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QAction, QCursor, QGuiApplication, QIcon, QPixmap, QRegion
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon, QWidget


CELL_WIDTH = 192
CELL_HEIGHT = 208
SHEET_SIZE = (1536, 1872)
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
FRAME_INTERVAL_MS = 160
MOVE_INTERVAL_MS = 33
WALK_SPEED = 48.0  # Qt's device-independent pixels per second


def sheet_path() -> Path:
    # PyInstaller's one-folder build keeps bundled data under _MEIPASS.
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / "pet" / "ling" / "spritesheet.webp"


def load_frames(path: Path) -> dict[str, list[QPixmap]]:
    with Image.open(path) as source:
        if source.size != SHEET_SIZE:
            raise ValueError(f"Expected a {SHEET_SIZE[0]}×{SHEET_SIZE[1]} sprite sheet")
        sheet = source.convert("RGBA")

    frames = {}
    for name, (row, count) in ANIMATIONS.items():
        images = []
        for column in range(count):
            frame = sheet.crop(
                (
                    column * CELL_WIDTH,
                    row * CELL_HEIGHT,
                    (column + 1) * CELL_WIDTH,
                    (row + 1) * CELL_HEIGHT,
                )
            )
            # PNG transfer avoids depending on Qt's optional WebP image plugin.
            buffer = io.BytesIO()
            frame.save(buffer, format="PNG")
            pixmap = QPixmap()
            if not pixmap.loadFromData(buffer.getvalue(), "PNG"):
                raise ValueError(f"Could not load {name} frame {column}")
            images.append(pixmap)
        frames[name] = images
    return frames


class LingWindow(QWidget):
    def __init__(self, frames: dict[str, list[QPixmap]]) -> None:
        super().__init__()
        self.frames = frames
        self.rng = random.Random()
        self.state = "idle"
        self.frame_index = 0
        self.direction = 1
        self.walking = False
        self.paused = False
        self.hovering = False
        self.reaction: str | None = None
        self.drag_offset: QPoint | None = None
        self.press_position: QPoint | None = None
        self.dragged = False
        self.x_position = 0.0
        self.phase_ends_at = time.monotonic() + 3.0
        self.last_tick = time.monotonic()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(CELL_WIDTH, CELL_HEIGHT)
        # A fixed union avoids spurious leave events when animated silhouettes change.
        input_region = QRegion()
        for animation in frames.values():
            for pixmap in animation:
                input_region |= QRegion(pixmap.mask())
        self.input_region = input_region
        self.setMask(input_region)

        self.menu = QMenu(self)
        self.pause_action = QAction("暂停行走", self)
        self.pause_action.triggered.connect(self.toggle_pause)
        self.menu.addAction(self.pause_action)
        actions_menu = self.menu.addMenu("播放动作")
        for label, state in (
            ("挥手", "waving"),
            ("跳跃", "jumping"),
            ("等待", "waiting"),
            ("忙碌", "running"),
            ("检查", "review"),
            ("沮丧", "failed"),
        ):
            action = actions_menu.addAction(label)
            action.triggered.connect(lambda checked=False, name=state: self.start_reaction(name))
        self.menu.addSeparator()
        exit_action = QAction("退出 Ling", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(exit_action)

        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        self.screen = screen
        if screen is None:
            raise RuntimeError("No display was found")
        area = screen.availableGeometry()
        self.x_position = float(area.center().x() - CELL_WIDTH // 2)
        self.place_at_bottom()
        self.show_frame()

        self.frame_timer = QTimer(self)
        self.frame_timer.setInterval(FRAME_INTERVAL_MS)
        self.frame_timer.timeout.connect(self.next_frame)
        self.frame_timer.start()

        self.motion_timer = QTimer(self)
        self.motion_timer.setInterval(MOVE_INTERVAL_MS)
        self.motion_timer.timeout.connect(self.advance_motion)
        self.motion_timer.start()

    def bounds(self) -> tuple[int, int, int]:
        area = self.screen.availableGeometry()
        left = area.left()
        right = max(left, area.right() - self.width() + 1)
        bottom = area.bottom() - self.height() + 1
        return left, right, bottom

    def place_at_bottom(self) -> None:
        left, right, bottom = self.bounds()
        self.x_position = max(left, min(right, self.x_position))
        self.move(round(self.x_position), bottom)

    def show_frame(self) -> None:
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        from PySide6.QtGui import QPainter

        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.frames[self.state][self.frame_index])

    def next_frame(self) -> None:
        if self.reaction is not None and self.frame_index + 1 == len(self.frames[self.state]):
            if self.reaction == "jumping" and self.hovering:
                self.frame_index = 0
                self.show_frame()
            elif self.hovering:
                self.start_reaction("jumping")
            else:
                self.stop_reaction()
            return
        self.frame_index = (self.frame_index + 1) % len(self.frames[self.state])
        self.show_frame()

    def set_state(self, state: str) -> None:
        if state != self.state:
            self.state = state
            self.frame_index = 0
            self.show_frame()

    def start_reaction(self, state: str) -> None:
        self.reaction = state
        self.walking = False
        self.state = state
        self.frame_index = 0
        self.show_frame()

    def stop_reaction(self) -> None:
        self.reaction = None
        self.walking = False
        self.phase_ends_at = time.monotonic() + 3.0
        self.set_state("idle")

    def refresh_hover(self) -> None:
        if self.drag_offset is not None or self.menu.isVisible():
            return
        hovered = self.input_region.contains(self.mapFromGlobal(QCursor.pos()))
        if hovered == self.hovering:
            return
        self.hovering = hovered
        if hovered:
            self.start_reaction("jumping")
        elif self.reaction == "jumping":
            self.stop_reaction()

    def advance_motion(self) -> None:
        now = time.monotonic()
        elapsed = min(now - self.last_tick, 0.1)
        self.last_tick = now
        self.refresh_hover()
        if self.paused or self.drag_offset is not None or self.reaction is not None:
            return

        if now >= self.phase_ends_at:
            self.walking = not self.walking
            if self.walking:
                self.direction = self.rng.choice((-1, 1))
                self.phase_ends_at = now + self.rng.uniform(2.0, 6.0)
            else:
                self.phase_ends_at = now + 3.0

        if not self.walking:
            self.set_state("idle")
            return

        left, right, _ = self.bounds()
        self.x_position += self.direction * WALK_SPEED * elapsed
        if self.x_position <= left:
            self.x_position = float(left)
            self.direction = 1
        elif self.x_position >= right:
            self.x_position = float(right)
            self.direction = -1
        self.set_state("right" if self.direction > 0 else "left")
        self.place_at_bottom()

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.walking = False
        self.phase_ends_at = time.monotonic() + 3.0
        if self.reaction is None:
            self.set_state("idle")
        self.pause_action.setText("继续行走" if self.paused else "暂停行走")

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.pos()
            self.press_position = event.globalPosition().toPoint()
            self.dragged = False
            self.walking = False
            self.reaction = None
            self.set_state("idle")
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.menu.exec(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self.drag_offset is not None and self.press_position is not None:
            if (event.globalPosition().toPoint() - self.press_position).manhattanLength() > 4:
                self.dragged = True
        if self.drag_offset is not None and self.dragged:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton and self.drag_offset is not None:
            self.drag_offset = None
            self.press_position = None
            if self.dragged:
                self.screen = QGuiApplication.screenAt(event.globalPosition().toPoint()) or self.screen
                self.x_position = float(self.x())
                self.place_at_bottom()
                self.phase_ends_at = time.monotonic() + 3.0
            else:
                self.start_reaction("waving")
            event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    try:
        frames = load_frames(sheet_path())
        window = LingWindow(frames)
    except (OSError, ValueError, RuntimeError) as exc:
        QMessageBox.critical(None, "Ling could not start", str(exc))
        return 1

    tray = QSystemTrayIcon(QIcon(frames["idle"][0]), app)
    tray.setToolTip("Ling")
    tray.setContextMenu(window.menu)
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray.show()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

"""Standalone Windows desktop companion for Ling."""

from __future__ import annotations

import io
import os
import random
import sys
import time
from pathlib import Path

from PIL import Image
from window_perch import WindowsDesktop, choose_attachment, ledge_position

if sys.platform == "win32":
    # Other desktop tools may put an incompatible ICU DLL on PATH. Load the
    # Windows copy before Qt so its unversioned ICU entry points resolve.
    import ctypes

    ctypes.WinDLL(str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "icuuc.dll"))

from PySide6.QtCore import QPoint, QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QCursor, QGuiApplication, QIcon, QPixmap, QRegion
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon, QToolTip, QWidget


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
PERCH_TOP_PADDING = 84
PERCH_ANCHORS = {"ling": (96, 104), "ling-heart": (96, 104)}
HANG_ANCHORS = {"ling": (96, 10), "ling-heart": (96, 10)}
HANG_GRIP_OFFSETS = {"ling": (-22, 22), "ling-heart": (-16.56, 16.56)}
HANG_FRAME_INTERVAL_MS = 250
SKINS = {
    "ling": "银色原版",
    "ling-heart": "红心白帽",
}


def settings_path() -> Path:
    app_data = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "LingWithMe"
    app_data.mkdir(parents=True, exist_ok=True)
    return app_data / "settings.ini"


def sheet_path(skin_id: str = "ling") -> Path:
    # PyInstaller's one-folder build keeps bundled data under _MEIPASS.
    if skin_id not in SKINS:
        raise ValueError(f"Unknown Ling skin: {skin_id}")
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / "pet" / skin_id / "spritesheet.webp"


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
    for name, filename, count in (("perched", "perch.png", 6), ("hanging", "hang.png", 8)):
        with Image.open(path.with_name(filename)) as source:
            if source.size != (CELL_WIDTH * count, CELL_HEIGHT):
                raise ValueError(f"Expected {count} cells in {filename}")
            images = []
            for column in range(count):
                buffer = io.BytesIO()
                source.crop((column * CELL_WIDTH, 0, (column + 1) * CELL_WIDTH, CELL_HEIGHT)).save(buffer, format="PNG")
                pixmap = QPixmap()
                if not pixmap.loadFromData(buffer.getvalue(), "PNG"):
                    raise ValueError(f"Could not load {filename} frame")
                images.append(pixmap)
            frames[name] = images
    return frames


class LingWindow(QWidget):
    def __init__(self, frame_sets: dict[str, dict[str, list[QPixmap]]], skin_id: str) -> None:
        super().__init__()
        self.frame_sets = frame_sets
        self.skin_id = skin_id
        self.frames = frame_sets[skin_id]
        self.settings = QSettings(str(settings_path()), QSettings.Format.IniFormat)
        self.tray: QSystemTrayIcon | None = None
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
        self.desktop = WindowsDesktop()
        self.perch_handle: int | None = None
        self.perch_edge = "top"
        self.perch_offset = 0.0
        self.drag_hint = ""

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(CELL_WIDTH, CELL_HEIGHT)
        # A fixed union avoids spurious leave events when animated silhouettes change.
        self.update_input_region()

        self.menu = QMenu(self)
        self.pause_action = QAction("暂停活动", self)
        self.pause_action.triggered.connect(self.toggle_pause)
        self.menu.addAction(self.pause_action)
        self.menu.addAction("回到桌面底边", self.return_to_desktop)
        wardrobe_menu = self.menu.addMenu("变装")
        wardrobe_group = QActionGroup(self)
        wardrobe_group.setExclusive(True)
        self.skin_actions = {}
        for variant, label in SKINS.items():
            action = wardrobe_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(variant == self.skin_id)
            wardrobe_group.addAction(action)
            action.triggered.connect(lambda checked=False, name=variant: self.change_skin(name))
            self.skin_actions[variant] = action
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
        self.perch_timer = QTimer(self)
        self.perch_timer.setInterval(100)
        self.perch_timer.timeout.connect(self.follow_window)
        self.perch_timer.start()

    def screen_rects(self):
        return [(s.geometry().x(), s.geometry().y(),
                 s.geometry().x() + s.geometry().width(),
                 s.geometry().y() + s.geometry().height()) for s in QGuiApplication.screens()]

    def return_to_desktop(self) -> None:
        self.perch_handle = None
        self.screen = self.nearest_screen(self.pos() + QPoint(96, 104))
        self.x_position = float(self.x())
        self.hovering = False
        self.stop_reaction()
        self.place_at_bottom()

    def nearest_screen(self, point):
        screen = QGuiApplication.screenAt(point)
        if screen is not None:
            return screen
        def distance(screen):
            rect = screen.geometry()
            dx = max(rect.left() - point.x(), 0, point.x() - rect.right())
            dy = max(rect.top() - point.y(), 0, point.y() - rect.bottom())
            return dx * dx + dy * dy
        return min(QGuiApplication.screens(), key=distance)

    def find_perch(self):
        windows = self.desktop.windows(QGuiApplication.screens())
        screens = self.screen_rects()
        region = QRegion()
        for pixmap in self.frames["idle"]:
            region |= QRegion(pixmap.mask())
        body = region.boundingRect().translated(self.pos())
        sprite_rect = (body.x(), body.y(), body.x() + body.width(), body.y() + body.height())
        return choose_attachment(windows, sprite_rect, self.attachment_anchors(),
                                 self.attachment_sizes(), screens, grip_offsets=HANG_GRIP_OFFSETS[self.skin_id])

    def attachment_anchors(self):
        return {"top": PERCH_ANCHORS[self.skin_id], "bottom": HANG_ANCHORS[self.skin_id]}

    def attachment_sizes(self):
        return {"top": (self.width(), self.height() - PERCH_TOP_PADDING),
                "bottom": (self.width(), self.height())}

    def resting_state(self):
        if self.perch_handle is None:
            return "idle"
        return "hanging" if self.perch_edge == "bottom" else "perched"

    def try_perch(self) -> bool:
        if not self.dragged:
            return False
        choice = self.find_perch()
        if choice is None:
            return False
        window, self.perch_offset, position, self.perch_edge = choice
        self.perch_handle = window.handle
        self.hovering = False
        self.reaction = None
        self.walking = False
        self.set_state(self.resting_state())
        self.move(round(position[0]), round(position[1]))
        return True

    def follow_window(self) -> None:
        if self.perch_handle is None or self.drag_offset is not None:
            return
        windows = self.desktop.windows(QGuiApplication.screens())
        target = next((w for w in windows if w.handle == self.perch_handle and w.candidate), None)
        position = None if target is None else ledge_position(
            target, self.perch_offset, self.attachment_anchors()[self.perch_edge],
            self.attachment_sizes()[self.perch_edge], self.screen_rects(), windows, self.perch_edge,
            HANG_GRIP_OFFSETS[self.skin_id])
        if position is None:
            self.return_to_desktop()
            return
        self.move(round(position[0]), round(position[1]))
        self.x_position = float(self.x())
        self.screen = self.nearest_screen(self.pos() + QPoint(*self.attachment_anchors()[self.perch_edge]))

    def bounds(self) -> tuple[int, int, int]:
        if self.screen not in QGuiApplication.screens():
            self.screen = QGuiApplication.primaryScreen()
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

    def update_input_region(self) -> None:
        region = QRegion()
        animations = ([self.frames[self.state]] if self.state in ("perched", "hanging") else
                      [v for k, v in self.frames.items() if k not in ("perched", "hanging")])
        for animation in animations:
            for pixmap in animation:
                if self.perch_handle is not None and self.reaction:
                    region |= QRegion(self.reaction_pixmap(pixmap).mask()).translated(47, 0)
                elif self.state == "perched":
                    region |= QRegion(pixmap.mask()).translated(0, -PERCH_TOP_PADDING)
                else:
                    region |= QRegion(pixmap.mask())
        self.input_region = region
        self.setMask(region)

    def change_skin(self, skin_id: str) -> None:
        if skin_id == self.skin_id:
            return
        self.skin_id = skin_id
        self.frames = self.frame_sets[skin_id]
        self.reaction = None
        self.walking = False
        self.hovering = False
        self.state = self.resting_state()
        self.frame_timer.setInterval(HANG_FRAME_INTERVAL_MS if self.state == "hanging" else FRAME_INTERVAL_MS)
        self.frame_index = 0
        self.phase_ends_at = time.monotonic() + 3.0
        self.update_input_region()
        self.skin_actions[skin_id].setChecked(True)
        self.settings.setValue("skin_id", skin_id)
        self.settings.sync()
        if self.tray is not None:
            self.tray.setIcon(QIcon(self.frames["idle"][0]))
        if self.perch_handle is not None:
            self.follow_window()
        else:
            self.place_at_bottom()
        self.show_frame()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        from PySide6.QtGui import QPainter

        painter = QPainter(self)
        pixmap = self.frames[self.state][self.frame_index]
        if self.perch_handle is not None and self.reaction:
            painter.drawPixmap(47, 0, self.reaction_pixmap(pixmap))
        elif self.state == "perched":
            painter.drawPixmap(0, -PERCH_TOP_PADDING, pixmap)
        else:
            painter.drawPixmap(0, 0, pixmap)

    def reaction_pixmap(self, pixmap: QPixmap) -> QPixmap:
        # Fit the standing gesture above the resting pose's ledge contact.
        return pixmap.scaled(98, 106, Qt.AspectRatioMode.IgnoreAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)

    def next_frame(self) -> None:
        if self.state == "hanging" and self.paused:
            return
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
            self.frame_timer.setInterval(HANG_FRAME_INTERVAL_MS if state == "hanging" else FRAME_INTERVAL_MS)
            self.update_input_region()
            self.show_frame()

    def start_reaction(self, state: str) -> None:
        if self.perch_handle is not None and self.perch_edge == "bottom":
            self.return_to_desktop()
        self.reaction = state
        self.walking = False
        self.state = state
        self.frame_index = 0
        self.frame_timer.setInterval(FRAME_INTERVAL_MS)
        self.update_input_region()
        self.show_frame()
        if self.perch_handle is not None:
            self.follow_window()

    def stop_reaction(self) -> None:
        self.reaction = None
        self.walking = False
        self.phase_ends_at = time.monotonic() + 3.0
        self.set_state(self.resting_state())
        if self.perch_handle is not None:
            self.follow_window()

    def refresh_hover(self) -> None:
        if self.perch_handle is not None or self.drag_offset is not None or self.menu.isVisible():
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
        if self.perch_handle is not None or self.paused or self.drag_offset is not None or self.reaction is not None:
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
            self.set_state(self.resting_state())
        self.pause_action.setText("继续活动" if self.paused else "暂停活动")

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.pos()
            self.press_position = event.globalPosition().toPoint()
            self.dragged = False
            self.drag_hint = ""
            self.walking = False
            self.reaction = None
            self.hovering = False
            self.set_state(self.resting_state())
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.menu.exec(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self.drag_offset is not None and self.press_position is not None:
            if (event.globalPosition().toPoint() - self.press_position).manhattanLength() > 4:
                self.dragged = True
        if self.drag_offset is not None and self.dragged:
            self.perch_handle = None
            self.set_state("idle")
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            pointer = event.globalPosition().toPoint()
            choice = self.find_perch()
            hint = ("松开即可抓住这个窗口下沿" if choice and choice[3] == "bottom" else
                    "松开即可趴在这个窗口上沿" if choice else
                    "让人偶身体碰到窗口上沿或下沿，上沿需留约 105 像素空间")
            if hint != self.drag_hint:
                self.drag_hint = hint
                QToolTip.showText(pointer + QPoint(16, 16), hint, self, self.rect(), 10000)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton and self.drag_offset is not None:
            QToolTip.hideText()
            self.drag_offset = None
            self.press_position = None
            if self.dragged:
                self.screen = QGuiApplication.screenAt(event.globalPosition().toPoint()) or self.screen
                self.x_position = float(self.x())
                if not self.try_perch():
                    self.return_to_desktop()
                    QToolTip.showText(event.globalPosition().toPoint(),
                                      "未能停靠：让人偶身体与窗口上沿或下沿重叠，上沿空间不足时请将窗口下移", self, self.rect(), 4000)
                self.phase_ends_at = time.monotonic() + 3.0
            elif self.resting_state() != "hanging":
                self.start_reaction("waving")
            self.dragged = False
            event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    try:
        frame_sets = {skin_id: load_frames(sheet_path(skin_id)) for skin_id in SKINS}
        saved_skin = QSettings(str(settings_path()), QSettings.Format.IniFormat).value("skin_id", "ling")
        skin_id = saved_skin if saved_skin in SKINS else "ling"
        window = LingWindow(frame_sets, skin_id)
    except (OSError, ValueError, RuntimeError) as exc:
        QMessageBox.critical(None, "Ling could not start", str(exc))
        return 1

    tray = QSystemTrayIcon(QIcon(window.frames["idle"][0]), app)
    window.tray = tray
    tray.setToolTip("Ling")
    tray.setContextMenu(window.menu)
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray.show()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

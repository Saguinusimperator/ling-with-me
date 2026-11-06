"""Standalone desktop companion for Ling (Windows and macOS)."""

from __future__ import annotations

import io
import os
import random
import sys
import time
from pathlib import Path

from PIL import Image

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"

from window_perch import WindowsDesktop, choose_attachment, ledge_position

if IS_MACOS:
    from macos_perch import MacDesktop

if IS_WINDOWS:
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
ANIMATION_CYCLE_MS = 1600
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
    if IS_MACOS:
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    app_data = base / "LingWithMe"
    app_data.mkdir(parents=True, exist_ok=True)
    return app_data / "settings.ini"


def confirm_microsoft_runtime_terms() -> bool:
    # Only the Windows bundle ships the Microsoft Visual C++ runtime.
    if not IS_WINDOWS:
        return True
    settings = QSettings(str(settings_path()), QSettings.Format.IniFormat)
    if settings.value("microsoft_terms_accepted_v1", False, type=bool):
        return True

    message = QMessageBox()
    message.setWindowTitle("Microsoft 运行库使用条款")
    message.setText("小灵包含运行所需的 Microsoft Visual C++ 组件。")
    message.setInformativeText(
        "Microsoft 保留这些组件的权利。选择“我同意”表示您同意：仅随小灵使用这些文件；"
        "不修改或单独分发；不暗示 Microsoft 认可小灵；除法律允许外，不对这些文件进行逆向工程。"
        "完整条款见解压目录中的 MICROSOFT-TERMS.md。"
    )
    agree = message.addButton("我已阅读并同意", QMessageBox.ButtonRole.AcceptRole)
    message.addButton("不同意并退出", QMessageBox.ButtonRole.RejectRole)
    message.exec()
    if message.clickedButton() is not agree:
        return False
    settings.setValue("microsoft_terms_accepted_v1", True)
    settings.sync()
    return True


def sheet_path(skin_id: str = "ling", scale: int = 1) -> Path:
    # PyInstaller's one-folder build keeps bundled data under _MEIPASS.
    if skin_id not in SKINS:
        raise ValueError(f"Unknown Ling skin: {skin_id}")
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    name = "spritesheet@2x.webp" if scale == 2 else "spritesheet.webp"
    return root / "pet" / skin_id / name


def preferred_scale() -> int:
    """Use the 2x artwork only on Retina macOS, and only when it is bundled."""
    if not IS_MACOS:
        return 1
    screen = QGuiApplication.primaryScreen()
    if screen is None or screen.devicePixelRatio() < 1.5:
        return 1
    return 2 if sheet_path("ling", 2).exists() else 1


def load_frames(path: Path, scale: int = 1) -> dict[str, list[QPixmap]]:
    cell_width, cell_height = CELL_WIDTH * scale, CELL_HEIGHT * scale
    sheet_size = (SHEET_SIZE[0] * scale, SHEET_SIZE[1] * scale)
    with Image.open(path) as source:
        if source.size != sheet_size:
            raise ValueError(f"Expected a {sheet_size[0]}×{sheet_size[1]} sprite sheet")
        sheet = source.convert("RGBA")

    frames = {}
    for name, (row, count) in ANIMATIONS.items():
        images = []
        for column in range(count):
            frame = sheet.crop(
                (
                    column * cell_width,
                    row * cell_height,
                    (column + 1) * cell_width,
                    (row + 1) * cell_height,
                )
            )
            # PNG transfer avoids depending on Qt's optional WebP image plugin.
            buffer = io.BytesIO()
            frame.save(buffer, format="PNG")
            pixmap = QPixmap()
            if not pixmap.loadFromData(buffer.getvalue(), "PNG"):
                raise ValueError(f"Could not load {name} frame {column}")
            pixmap.setDevicePixelRatio(scale)
            images.append(pixmap)
        frames[name] = images
    for name, filename, count in (("perched", "perch.png", 6), ("hanging", "hang.png", 8)):
        strip_name = f"{Path(filename).stem}@2x.png" if scale == 2 else filename
        with Image.open(path.with_name(strip_name)) as source:
            if source.size != (cell_width * count, cell_height):
                raise ValueError(f"Expected {count} cells in {strip_name}")
            images = []
            for column in range(count):
                buffer = io.BytesIO()
                source.crop((column * cell_width, 0, (column + 1) * cell_width, cell_height)).save(buffer, format="PNG")
                pixmap = QPixmap()
                if not pixmap.loadFromData(buffer.getvalue(), "PNG"):
                    raise ValueError(f"Could not load {strip_name} frame")
                pixmap.setDevicePixelRatio(scale)
                images.append(pixmap)
            frames[name] = images
    return frames


def pixmap_region(pixmap: QPixmap) -> QRegion:
    """Hit region in widget (logical) coordinates, including for 2x pixmaps."""
    ratio = pixmap.devicePixelRatio()
    if ratio <= 1.0:
        return QRegion(pixmap.mask())
    image = pixmap.toImage().scaled(
        round(pixmap.width() / ratio),
        round(pixmap.height() / ratio),
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.FastTransformation,
    )
    return QRegion(QPixmap.fromImage(image).mask())


class LingWindow(QWidget):
    def __init__(self, frame_sets: dict[str, dict[str, list[QPixmap]]], skin_id: str) -> None:
        super().__init__()
        self.frame_sets = frame_sets
        self.skin_id = skin_id
        self.frames = frame_sets[skin_id]
        self.frame_regions = self.build_frame_regions()
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
        self.playback_mode = "auto"
        self.cycles_left = 2
        self.animation_queue: list[str] = []
        self.last_auto_state: str | None = None
        self.drag_offset: QPoint | None = None
        self.press_position: QPoint | None = None
        self.dragged = False
        self.x_position = 0.0
        self.last_tick = time.monotonic()
        self.desktop = WindowsDesktop() if IS_WINDOWS else MacDesktop() if IS_MACOS else None
        self.perch_supported = self.desktop is not None
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
        if IS_MACOS:
            # Qt hides a Tool window when the app deactivates; the pet must stay
            # visible while the user works in other applications.
            self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)
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
            ("待机", "idle"),
            ("向右走", "right"),
            ("向左走", "left"),
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
        self.frame_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.frame_timer.timeout.connect(self.next_frame)
        self.frame_timer.start()
        self.start_next_auto()

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

    def return_to_desktop(self, *, resume: bool = True) -> None:
        self.perch_handle = None
        self.screen = self.nearest_screen(self.pos() + QPoint(96, 104))
        self.x_position = float(self.x())
        self.hovering = False
        if resume:
            self.stop_reaction()
        else:
            self.begin_animation("idle", "rest")
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
        if self.desktop is None:
            return None
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
        if not self.perch_supported or not self.dragged:
            return False
        choice = self.find_perch()
        if choice is None:
            return False
        window, self.perch_offset, position, self.perch_edge = choice
        self.perch_handle = window.handle
        self.hovering = False
        self.reaction = None
        self.walking = False
        self.begin_animation(self.resting_state(), "rest")
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

    def build_frame_regions(self) -> dict[str, list[QRegion]]:
        return {name: [pixmap_region(pixmap) for pixmap in frames] for name, frames in self.frames.items()}

    def update_input_region(self) -> None:
        region = QRegion()
        names = ([self.state] if self.state in ("perched", "hanging") else
                 [name for name in self.frames if name not in ("perched", "hanging")])
        for name in names:
            for pixmap, base in zip(self.frames[name], self.frame_regions[name]):
                if self.perch_handle is not None and self.reaction:
                    region |= pixmap_region(self.reaction_pixmap(pixmap)).translated(47, 0)
                elif self.state == "perched":
                    region |= base.translated(0, -PERCH_TOP_PADDING)
                else:
                    region |= base
        self.input_region = region
        self.setMask(region)

    def change_skin(self, skin_id: str) -> None:
        if skin_id == self.skin_id:
            return
        self.skin_id = skin_id
        self.frames = self.frame_sets[skin_id]
        self.frame_regions = self.build_frame_regions()
        self.reaction = None
        self.walking = False
        self.hovering = False
        self.stop_reaction()
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
        if IS_MACOS:
            # Retina backing stores upscale the 1x sprite sheet; keep it smooth.
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        pixmap = self.frames[self.state][self.frame_index]
        if self.perch_handle is not None and self.reaction:
            painter.drawPixmap(47, 0, self.reaction_pixmap(pixmap))
        elif self.state == "perched":
            painter.drawPixmap(0, -PERCH_TOP_PADDING, pixmap)
        else:
            painter.drawPixmap(0, 0, pixmap)

    def reaction_pixmap(self, pixmap: QPixmap) -> QPixmap:
        # Fit the standing gesture above the resting pose's ledge contact.
        ratio = pixmap.devicePixelRatio()
        scaled = pixmap.scaled(round(98 * ratio), round(106 * ratio),
                               Qt.AspectRatioMode.IgnoreAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        scaled.setDevicePixelRatio(ratio)
        return scaled

    def next_frame(self) -> None:
        if self.drag_offset is not None or (self.paused and self.playback_mode != "manual"):
            return
        if self.frame_index + 1 == len(self.frames[self.state]):
            if self.playback_mode in ("auto", "manual"):
                self.cycles_left -= 1
                if self.cycles_left == 0:
                    self.stop_reaction()
                    return
            elif self.playback_mode == "hover" and not self.hovering:
                self.stop_reaction()
                return
        self.frame_index = (self.frame_index + 1) % len(self.frames[self.state])
        self.show_frame()

    def frame_interval(self, state: str) -> int:
        if state == "hanging":
            return HANG_FRAME_INTERVAL_MS
        return round(ANIMATION_CYCLE_MS / len(self.frames[state]))

    def set_state(self, state: str, *, restart: bool = False) -> None:
        if state != self.state or restart:
            self.state = state
            if restart:
                self.frame_index = 0
                self.frame_timer.setInterval(self.frame_interval(state))
            self.update_input_region()
            self.show_frame()

    def begin_animation(self, state: str, mode: str, cycles: int = 0) -> None:
        self.playback_mode = mode
        self.cycles_left = cycles
        self.reaction = state if mode in ("manual", "hover") else None
        self.walking = state in ("left", "right") and self.perch_handle is None
        if self.walking:
            self.direction = 1 if state == "right" else -1
        self.set_state(state, restart=True)

    def start_next_auto(self) -> None:
        if not self.animation_queue:
            self.animation_queue = list(ANIMATIONS)
            self.rng.shuffle(self.animation_queue)
            if self.animation_queue[-1] == self.last_auto_state:
                self.animation_queue[0], self.animation_queue[-1] = self.animation_queue[-1], self.animation_queue[0]
        state = self.animation_queue.pop()
        self.last_auto_state = state
        self.begin_animation(state, "auto", 2)

    def start_reaction(self, state: str, *, mode: str = "manual") -> None:
        if self.perch_handle is not None and self.perch_edge == "bottom":
            self.return_to_desktop(resume=False)
        self.begin_animation(state, mode, 1)
        if self.perch_handle is not None:
            self.follow_window()

    def stop_reaction(self) -> None:
        if self.perch_handle is None and not self.paused and self.drag_offset is None:
            self.start_next_auto()
        else:
            self.begin_animation(self.resting_state(), "rest")
        if self.perch_handle is not None:
            self.follow_window()

    def refresh_hover(self) -> None:
        if self.perch_handle is not None or self.drag_offset is not None or self.menu.isVisible():
            return
        hovered = self.input_region.contains(self.mapFromGlobal(QCursor.pos()))
        if hovered == self.hovering:
            return
        self.hovering = hovered
        if self.playback_mode == "manual" or self.paused:
            return
        if hovered:
            self.start_reaction("jumping", mode="hover")
        elif self.playback_mode == "hover":
            self.stop_reaction()

    def advance_motion(self) -> None:
        now = time.monotonic()
        elapsed = min(now - self.last_tick, 0.1)
        self.last_tick = now
        self.refresh_hover()
        if self.perch_handle is not None or self.drag_offset is not None or (self.paused and self.playback_mode != "manual"):
            return
        if not self.walking:
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
        if not self.paused and self.playback_mode == "rest" and self.perch_handle is None:
            self.start_next_auto()
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
            self.begin_animation(self.resting_state(), "rest")
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
            self.begin_animation("idle", "rest")
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            pointer = event.globalPosition().toPoint()
            if self.perch_supported:
                choice = self.find_perch()
                hint = (getattr(self.desktop, "unavailable_reason", "") or
                        ("松开即可抓住这个窗口下沿" if choice and choice[3] == "bottom" else
                        "松开即可趴在这个窗口上沿" if choice else
                        "让人偶身体碰到窗口上沿或下沿，上沿需留约 105 像素空间"))
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
                    if self.perch_supported:
                        QToolTip.showText(event.globalPosition().toPoint(),
                                          getattr(self.desktop, "unavailable_reason", "") or
                                          "未能停靠：让人偶身体与窗口上沿或下沿重叠，上沿空间不足时请将窗口下移", self, self.rect(), 4000)
            elif self.resting_state() != "hanging":
                self.start_reaction("waving")
            self.dragged = False
            event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    if not confirm_microsoft_runtime_terms():
        return 0
    try:
        scale = preferred_scale()
        frame_sets = {skin_id: load_frames(sheet_path(skin_id, scale), scale) for skin_id in SKINS}
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

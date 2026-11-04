r"""Real HWND/Qt integration check using an isolated, disposable fixture window.

Run .venv\Scripts\python tools\smoke_windows.py from the repository root.
Only controls its own fixture and Ling widgets; settings remain isolated.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ling_app as ling
from PySide6.QtCore import QPointF, QSettings, QTimer
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter
from PySide6.QtWidgets import QLabel, QLayout, QSystemTrayIcon, QVBoxLayout, QWidget


def fixture(command_path):
    app = ling.QApplication([])
    window = QWidget()
    window.setWindowTitle("Ling ledge smoke fixture")
    layout = QVBoxLayout(window)
    layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
    layout.addWidget(QLabel("Ling window ledge test\nDisposable test window"))
    window.setStyleSheet("background: #e6eef6; color: #243447; font-size: 24px;")
    window.setGeometry(250, 420, 700, 350)
    window.show()
    Path(command_path).with_suffix(".ready").write_text(str(int(window.winId())))
    last = None

    def poll():
        nonlocal last
        try:
            text = Path(command_path).read_text()
            if text == last:
                return
            command = json.loads(text)
            last = text
        except (OSError, ValueError):
            return
        action = command["action"]
        if action in ("geometry", "block"):
            if action == "block":
                window.setWindowFlag(ling.Qt.WindowType.WindowStaysOnTopHint, True)
            window.showNormal()
            window.setGeometry(*command["rect"])
            window.raise_()
        elif action == "minimize":
            window.showMinimized()
        elif action == "hide":
            window.hide()
        elif action == "maximize":
            window.showMaximized()
        elif action == "capture":
            window.grab().save(command["path"])
        elif action == "quit":
            app.quit()

    timer = QTimer()
    timer.timeout.connect(poll)
    timer.start(30)
    app.exec()


def main():
    app = ling.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    out = Path("build/perch-qa")
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ling-smoke-") as tmp:
        commands = Path(tmp) / "commands.json"
        child = subprocess.Popen([sys.executable, __file__, "--fixture", str(commands)])
        pet = None
        checks = []

        def wait(ms=300):
            end = time.monotonic() + ms / 1000
            while time.monotonic() < end:
                app.processEvents()
                time.sleep(0.01)

        def command(action, **kwargs):
            commands.write_text(json.dumps({"action": action, "nonce": time.monotonic(), **kwargs}))
            wait()

        def target():
            handle = int(commands.with_suffix(".ready").read_text())
            return next(w for w in pet.desktop.windows(app.screens()) if w.handle == handle)

        def check(label, condition):
            assert condition, label
            checks.append(label)

        def attach():
            window = target()
            anchor = ling.PERCH_ANCHORS[pet.skin_id]
            pet.move(round(window.rect[0] + 240 - anchor[0]), round(window.rect[1] - 204))
            check("native window attach", pet.try_perch())
            wait()
            return window

        def mouse(kind, local, global_pos, button, buttons):
            event = QMouseEvent(kind, QPointF(*local), QPointF(*global_pos), button, buttons, ling.Qt.KeyboardModifier.NoModifier)
            app.sendEvent(pet, event)

        try:
            frames = {skin: ling.load_frames(ling.sheet_path(skin)) for skin in ling.SKINS}
            with patch.object(ling, "settings_path", return_value=Path(tmp) / "settings.ini"):
                pet = ling.LingWindow(frames, "ling")
            pet.show()
            wait(1000)
            check("both skins have six transparent perch frames", all(len(f["perched"]) == 6 for f in frames.values()))
            check("desktop startup", pet.state == "idle" and pet.perch_handle is None)
            window = attach()
            pet.toggle_pause()
            command("geometry", rect=[340, 480, 600, 320])
            check("follow while paused", abs(pet.x() - (window.rect[0] + 90 + 240 - 96)) <= 2)
            check("no hover jump on ledge", pet.state == "perched")
            pet.start_reaction("waving")
            wait(850)
            check("wave returns to perch", pet.state == "perched" and pet.reaction is None)
            command("geometry", rect=[340, 150, 600, 320])
            pet.start_reaction("waving")
            wait(850)
            check("wave near screen top retains ledge", pet.perch_handle is not None and pet.state == "perched")
            command("geometry", rect=[340, 480, 600, 320])
            for skin in ling.SKINS:
                pet.change_skin(skin)
                wait()
                check("skin retains ledge: " + skin, pet.perch_handle is not None and pet.state == "perched")
                # Export live widget renders when desktop capture is unavailable.
                fixture_png = (out / "fixture.png").resolve()
                command("capture", path=str(fixture_png))
                image = QImage(700, 460, QImage.Format.Format_ARGB32)
                image.fill(QColor("#f6f8fb"))
                painter = QPainter(image)
                painter.setPen(QColor("#243447"))
                painter.drawText(20, 30, "Ling — live widget render preview")
                painter.drawImage(30, 220, QImage(str(fixture_png)))
                painter.fillRect(30, 190, 600, 30, QColor("#d4dfed"))
                painter.drawText(44, 210, "Ling window ledge test")
                painter.drawPixmap(30 + pet.x() - round(target().rect[0]), 190 - ling.PERCH_ANCHORS[skin][1], pet.grab())
                painter.end()
                image.save(str(out / (skin + "-render.png")))
            command("geometry", rect=[340, 480, 220, 320])
            check("resize clamps", pet.perch_handle is not None and abs(pet.x() - (target().rect[2] - 192)) <= 2)
            command("minimize")
            check("minimize detaches", pet.perch_handle is None)
            for action in ("hide", "maximize"):
                command("geometry", rect=[250, 420, 700, 350])
                attach()
                command(action)
                check(action + " detaches", pet.perch_handle is None)
            command("geometry", rect=[250, 420, 700, 350])
            attach()
            # A second fixture in front must invalidate the covered contact point.
            blocker_commands = Path(tmp) / "blocker.json"
            blocker = subprocess.Popen([sys.executable, __file__, "--fixture", str(blocker_commands)])
            try:
                blocker_commands.write_text(json.dumps({"action": "block", "rect": [300, 300, 650, 500]}))
                wait(700)
                check("covered ledge detaches", pet.perch_handle is None)
            finally:
                blocker_commands.write_text(json.dumps({"action": "quit"}))
                wait()
                blocker.wait(timeout=5)
            command("geometry", rect=[250, 420, 700, 350])
            # Exercise Qt drag events, including reattachment and drag-away.
            from PySide6.QtCore import QEvent
            left = ling.Qt.MouseButton.LeftButton
            none = ling.Qt.MouseButton.NoButton
            start = (pet.x()+96, pet.y()+104)
            destination = (450, target().rect[1] - 188 + 104)
            mouse(QEvent.Type.MouseButtonPress, (96,104), start, left, left)
            mouse(QEvent.Type.MouseMove, (96,104), destination, none, left)
            mouse(QEvent.Type.MouseButtonRelease, (96,104), destination, left, none)
            check("drag release attaches", pet.perch_handle is not None)
            check("drag shows release hint", pet.drag_hint == "松开即可趴在这个窗口上沿")
            start = (pet.x()+96, pet.y()+160)
            mouse(QEvent.Type.MouseButtonPress, (96,160), start, left, left)
            destination = (1100, 700)
            mouse(QEvent.Type.MouseMove, (96,160), destination, none, left)
            mouse(QEvent.Type.MouseButtonRelease, (96,160), destination, left, none)
            check("drag away restores desktop", pet.perch_handle is None)
            # Grab the head while the body overlaps the ledge: no foot alignment.
            command("geometry", rect=[250, 150, 700, 350])
            start = (pet.x()+96, pet.y()+35)
            destination = (450, target().rect[1]+20)
            mouse(QEvent.Type.MouseButtonPress, (96,35), start, left, left)
            mouse(QEvent.Type.MouseMove, (96,35), destination, none, left)
            mouse(QEvent.Type.MouseButtonRelease, (96,35), destination, left, none)
            check("head grab with body overlapping ledge attaches", pet.perch_handle is not None)
            check("resting artwork fits screen", pet.y() >= 0)
            pet.return_to_desktop()
            pet.toggle_pause()
            pet.hovering = False
            pet.phase_ends_at = time.monotonic() - 1
            pet.advance_motion()
            check("walk resumes", pet.walking and pet.state in ("left", "right"))
            pet.start_reaction("jumping")
            wait(1000)
            check("jump completes", pet.reaction is None)
            attach()
            if len(app.screens()) > 1:
                screen = app.screens()[1].geometry()
                command("geometry", rect=[screen.x()+100, screen.y()+450, 650, 350])
                check("second monitor follows", pet.perch_handle is not None and pet.screen == app.screens()[1])
                command("geometry", rect=[250, 420, 700, 350])
                check("returns across monitors", pet.perch_handle is not None and pet.screen == app.screens()[0])
            command("quit")
            child.wait(timeout=5)
            wait()
            check("closed window detaches", pet.perch_handle is None)
            pet.return_to_desktop()
            check("return to desktop", pet.y() == pet.bounds()[2])
            for origin in ("pet menu", "tray menu"):
                tray = QSystemTrayIcon(pet)
                tray.setContextMenu(pet.menu)
                menu = pet.menu if origin == "pet menu" else tray.contextMenu()
                exit_action = next(a for a in menu.actions() if a.text() == "退出 Ling")
                QTimer.singleShot(0, exit_action.trigger)
                check(origin + " exits", app.exec() == 0)
            report = {"checks": checks, "screens": [(s.name(), s.devicePixelRatio(), s.geometry().getRect()) for s in app.screens()]}
            (out / "smoke.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False, indent=2))
        finally:
            if pet:
                pet.close()
            if child.poll() is None:
                commands.write_text(json.dumps({"action": "quit"}))
                wait()
                child.wait(timeout=5)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--fixture":
        fixture(sys.argv[2])
    else:
        main()

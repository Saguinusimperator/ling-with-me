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
from PySide6.QtCore import QEvent, QPointF, QSettings, QTimer
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
            start = (pet.x()+96, pet.y()+104)
            destination = (window.rect[0]+240, window.rect[1]-100)
            mouse(QEvent.Type.MouseButtonPress, (96,104), start, ling.Qt.MouseButton.LeftButton, ling.Qt.MouseButton.LeftButton)
            mouse(QEvent.Type.MouseMove, (96,104), destination, ling.Qt.MouseButton.NoButton, ling.Qt.MouseButton.LeftButton)
            mouse(QEvent.Type.MouseButtonRelease, (96,104), destination, ling.Qt.MouseButton.LeftButton, ling.Qt.MouseButton.NoButton)
            check("native window attach", pet.perch_handle is not None and pet.perch_edge == "top")
            wait()
            return window

        def mouse(kind, local, global_pos, button, buttons):
            event = QMouseEvent(kind, QPointF(*local), QPointF(*global_pos), button, buttons, ling.Qt.KeyboardModifier.NoModifier)
            app.sendEvent(pet, event)

        def hang():
            window = target()
            start = (pet.x()+96, pet.y()+104)
            destination = (window.rect[0]+min(240, (window.rect[2]-window.rect[0])/2), window.rect[3])
            mouse(QEvent.Type.MouseButtonPress, (96,104), start, ling.Qt.MouseButton.LeftButton, ling.Qt.MouseButton.LeftButton)
            mouse(QEvent.Type.MouseMove, (96,104), destination, ling.Qt.MouseButton.NoButton, ling.Qt.MouseButton.LeftButton)
            check("drag preview does not bind", pet.perch_handle is None)
            check("lower edge release hint", pet.drag_hint == "松开即可抓住这个窗口下沿")
            mouse(QEvent.Type.MouseButtonRelease, (96,104), destination, ling.Qt.MouseButton.LeftButton, ling.Qt.MouseButton.NoButton)
            check("release binds hanging", pet.state == "hanging" and pet.perch_edge == "bottom")
            wait()

        try:
            frames = {skin: ling.load_frames(ling.sheet_path(skin)) for skin in ling.SKINS}
            with patch.object(ling, "settings_path", return_value=Path(tmp) / "settings.ini"):
                pet = ling.LingWindow(frames, "ling")
            pet.show()
            wait(1000)
            check("both skins have six transparent perch frames", all(len(f["perched"]) == 6 for f in frames.values()))
            check("desktop startup", pet.state in ling.ANIMATIONS and pet.perch_handle is None)
            window = attach()
            pet.toggle_pause()
            command("geometry", rect=[340, 480, 600, 320])
            check("follow while paused", abs(pet.x() - (window.rect[0] + 90 + 240 - 96)) <= 2)
            check("no hover jump on ledge", pet.state == "perched")
            pet.start_reaction("waving")
            wait(1750)
            check("wave returns to perch", pet.state == "perched" and pet.reaction is None)
            command("geometry", rect=[340, 150, 600, 320])
            pet.start_reaction("waving")
            wait(1750)
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
            pet.begin_animation("right", "auto", 2)
            pet.advance_motion()
            check("walk resumes", pet.walking and pet.state in ("left", "right"))
            pet.start_reaction("jumping")
            wait(1750)
            check("jump completes", pet.reaction is None)
            attach()
            if len(app.screens()) > 1:
                screen = app.screens()[1].geometry()
                command("geometry", rect=[screen.x()+100, screen.y()+450, 650, 350])
                check("second monitor follows", pet.perch_handle is not None and pet.screen == app.screens()[1])
                command("geometry", rect=[250, 420, 700, 350])
                check("returns across monitors", pet.perch_handle is not None and pet.screen == app.screens()[0])
            pet.return_to_desktop()
            if not pet.paused:
                pet.toggle_pause()
            window = target()
            pet.move(round(window.rect[0]+144), round(window.rect[3]-104))
            pet.follow_window()
            pet.advance_motion()
            wait()
            check("stationary overlap does not bind", pet.perch_handle is None)
            check("binding rejects a call without dragging", not pet.try_perch())
            start = (pet.x()+96, pet.y()+104)
            mouse(QEvent.Type.MouseButtonPress, (96,104), start, left, left)
            mouse(QEvent.Type.MouseButtonRelease, (96,104), start, left, none)
            wait(1750)
            check("ordinary click on lower edge does not hang", pet.perch_handle is None)
            command("geometry", rect=[260, 430, 700, 350])
            check("window moving through pet does not hang", pet.perch_handle is None)
            pet.toggle_pause()
            pet.begin_animation("right", "auto", 2)
            pet.x_position = float(pet.x())
            pet.advance_motion()
            check("autonomous walking does not hang", pet.perch_handle is None)
            pet.toggle_pause()
            hang()
            frame = pet.frame_index
            pet.next_frame()
            check("pause freezes hanging swing", pet.frame_index == frame)
            command("geometry", rect=[300, 470, 650, 350])
            check("paused hanging follows window", abs(pet.y() - (target().rect[3]-10)) <= 1)
            pet.toggle_pause()
            frame = pet.frame_index
            wait(800)
            check("hanging swing resumes", pet.frame_index != frame and pet.frame_timer.interval() == 250)
            for skin in ling.SKINS:
                pet.change_skin(skin)
                check("hanging skin switch retains grips: " + skin,
                      pet.state == "hanging" and abs(pet.y() - (target().rect[3]-10)) <= 1)
                pet.frame_timer.stop()
                from PIL import Image
                gif_frames = []
                for i in range(8):
                    pet.frame_index = i
                    image = QImage(700, 400, QImage.Format.Format_ARGB32)
                    image.fill(QColor("#f6f8fb"))
                    painter = QPainter(image)
                    painter.setPen(QColor("#243447"))
                    painter.drawText(20, 28, "Ling — live widget render preview")
                    painter.fillRect(30, 50, 600, 100, QColor("#d4dfed"))
                    painter.drawText(45, 80, "Window bottom edge / hanging")
                    painter.drawPixmap(230, 140, pet.grab())
                    painter.end()
                    filename = out / f"{skin}-hang-{i}.png"
                    image.save(str(filename))
                    with Image.open(filename) as rendered:
                        gif_frames.append(rendered.convert("RGB"))
                gif_frames[0].save(out / f"{skin}-hanging.gif", save_all=True,
                                   append_images=gif_frames[1:], duration=250, loop=0)
                pet.frame_timer.start()
            start = (pet.x()+96, pet.y()+104)
            mouse(QEvent.Type.MouseButtonPress, (96,104), start, left, left)
            mouse(QEvent.Type.MouseButtonRelease, (96,104), start, left, none)
            pet.refresh_hover()
            check("click and hover retain both grips", pet.state == "hanging" and pet.reaction is None)
            command("geometry", rect=[300, 470, 220, 350])
            check("hanging resize clamps", abs(pet.x() - (target().rect[2]-192)) <= 2)
            if len(app.screens()) > 1:
                screen = app.screens()[1].geometry()
                command("geometry", rect=[screen.x()+100, screen.y()+450, 650, 350])
                check("hanging follows across monitors", pet.state == "hanging" and pet.screen == app.screens()[1])
            screen = app.screens()[0].geometry()
            command("geometry", rect=[250, screen.bottom()-250, 700, 300])
            check("body below screen stays hanging", pet.state == "hanging" and pet.y()+208 > screen.bottom())
            command("geometry", rect=[250, screen.bottom()-200, 700, 300])
            check("moving farther below screen does not clamp or detach",
                  pet.state == "hanging" and abs(pet.y() - (target().rect[3]-10)) <= 1)
            restore_action = next(a for a in pet.menu.actions() if a.text() == "回到桌面底边")
            restore_action.trigger()
            check("menu restores a clipped hanging pet", pet.perch_handle is None and pet.y() == pet.bounds()[2])
            command("geometry", rect=[250, 420, 700, 350])
            hang()
            pet.start_reaction("waving")
            check("manual action detaches hanging", pet.perch_handle is None and pet.state == "waving")
            wait(1750)
            hang()
            start = (pet.x()+96, pet.y()+104)
            destination = (1100, 300)
            mouse(QEvent.Type.MouseButtonPress, (96,104), start, left, left)
            mouse(QEvent.Type.MouseMove, (96,104), destination, none, left)
            check("dragging immediately releases hanging grips", pet.perch_handle is None)
            mouse(QEvent.Type.MouseButtonRelease, (96,104), destination, left, none)
            check("dragging away from hanging restores desktop", pet.perch_handle is None and pet.state in ling.ANIMATIONS)
            for action in ("minimize", "hide"):
                hang()
                command(action)
                check("hanging " + action + " detaches", pet.perch_handle is None)
                command("geometry", rect=[250, 420, 700, 350])
            hang()
            blocker = subprocess.Popen([sys.executable, __file__, "--fixture", str(blocker_commands)])
            try:
                blocker_commands.write_text(json.dumps({"action": "block", "rect": [300, 650, 650, 300]}))
                wait(900)
                check("covered lower grip detaches", pet.perch_handle is None)
            finally:
                blocker_commands.write_text(json.dumps({"action": "quit"}))
                wait()
                blocker.wait(timeout=5)
            hang()
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

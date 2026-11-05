"""Read visible macOS window geometry without requesting capture permission.

Quartz window bounds use global top-left coordinates in points, matching Qt's
logical desktop coordinates on macOS (including Retina displays).
"""

import os

from window_perch import WindowInfo

try:
    import Quartz
    from AppKit import NSRunningApplication
except ImportError:
    Quartz = None


class MacDesktop:
    def __init__(self):
        self.unavailable_reason = ""
        if Quartz is None:
            self.unavailable_reason = "窗口停靠不可用：请安装 pyobjc-framework-Quartz 后重新启动小灵"

    def windows(self, screens):
        if Quartz is None:
            return []
        try:
            entries = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
                Quartz.kCGNullWindowID,
            )
            if entries is None:
                self.unavailable_reason = "系统暂时无法读取窗口位置，小灵仍可在桌面底边活动"
                return []
        except Exception:
            self.unavailable_reason = "系统暂时无法读取窗口位置，小灵仍可在桌面底边活动"
            return []

        self.unavailable_reason = ""
        result = []
        dock_pids = set()
        for entry in entries:  # Quartz supplies front-to-back stacking order.
            try:
                pid = int(entry.get("kCGWindowOwnerPID", -1))
                if pid == os.getpid():
                    continue
                if not entry.get("kCGWindowIsOnscreen", True):
                    continue
                if float(entry.get("kCGWindowAlpha", 1)) <= 0:
                    continue
                layer = int(entry.get("kCGWindowLayer", 0))
                if layer < 0:  # Desktop wallpaper is never a ledge or occluder.
                    continue
                bounds = entry["kCGWindowBounds"]
                x, y = float(bounds["X"]), float(bounds["Y"])
                width, height = float(bounds["Width"]), float(bounds["Height"])
                handle = int(entry["kCGWindowNumber"])
                if width <= 0 or height <= 0:
                    continue
                # The Dock also owns an invisible full-display layer-20 helper.
                # Identify it by bundle ID, not its localized/redacted owner name.
                if layer == 20:
                    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
                    if app is not None and app.bundleIdentifier() == "com.apple.dock":
                        dock_pids.add(pid)
                    if pid in dock_pids and any(
                        x <= s.geometry().x() and y <= s.geometry().y()
                        and x + width >= s.geometry().x() + s.geometry().width()
                        and y + height >= s.geometry().y() + s.geometry().height()
                        for s in screens
                    ):
                        continue
                # Floating panels, menus and the visible Dock block contact points,
                # but only ordinary application windows can hold the pet.
                result.append(WindowInfo(handle, (x, y, x + width, y + height), layer == 0))
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
        return result

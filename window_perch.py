"""Window discovery and pure geometry for the Windows ledge behaviour.

Public rectangles use Qt logical desktop coordinates; native rectangles stay
physical until converted using the matching monitor's origin and scale.
"""

from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import os


@dataclass(frozen=True)
class WindowInfo:
    handle: int
    rect: tuple[float, float, float, float]
    candidate: bool = True


def logical_rect(rect, native_origin, logical_origin, scale):
    return tuple(logical_origin[i % 2] + (v - native_origin[i % 2]) / scale
                 for i, v in enumerate(rect))


def contains(rect, x, y):
    left, top, right, bottom = rect
    return left <= x < right and top <= y < bottom


def ledge_position(window, offset, anchor, size, screens, windows, edge="top", grip_offsets=(-22, 22)):
    left, top, right, bottom = window.rect
    width, height = size
    if right - left < width:
        return None
    x = max(left, min(right - width, left + offset - anchor[0]))
    edge_y = top if edge == "top" else bottom
    y = edge_y - anchor[1]
    if edge == "top" and not any(l <= x and t <= y and x + width <= r and y + height <= b
                                 for l, t, r, b in screens):
        return None
    # Hanging may extend below the display. Never clamp or detach vertically.
    if edge == "bottom" and not any(l <= x and x + width <= r for l, _, r, _ in screens):
        return None
    contact_x = x + anchor[0]
    contact_xs = tuple(contact_x + dx for dx in grip_offsets) if edge == "bottom" else (contact_x,)
    for other in windows:
        if other.handle == window.handle:
            return x, y
        if any(contains(other.rect, hand_x, edge_y + (1 if edge == "top" else -1))
               for hand_x in contact_xs):
            return None
    return None


def choose_attachment(windows, sprite_rect, anchors, sizes, screens, tolerance=28, grip_offsets=(-22, 22)):
    """Return a drag candidate only; the caller binds it on mouse release."""
    sprite_left, sprite_top, sprite_right, sprite_bottom = sprite_rect
    for window in windows:
        left, top, right, bottom = window.rect
        overlap_left, overlap_right = max(left, sprite_left), min(right, sprite_right)
        if not window.candidate or overlap_left >= overlap_right:
            continue
        contact_x = max(overlap_left, min(overlap_right - 1, (sprite_left + sprite_right) / 2))
        offset = contact_x - left
        center_y = (sprite_top + sprite_bottom) / 2
        edges = sorted((("top", top), ("bottom", bottom)), key=lambda e: abs(e[1] - center_y))
        for edge, edge_y in edges:  # Stable sorting makes ties prefer the top.
            if not sprite_top - tolerance <= edge_y <= sprite_bottom + tolerance:
                continue
            position = ledge_position(window, offset, anchors[edge], sizes[edge], screens, windows, edge, grip_offsets)
            if position is not None:
                return window, offset, position, edge
    return None


class WindowsDesktop:
    def __init__(self):
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.dwm = ctypes.WinDLL("dwmapi")
        self.callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        self.user.EnumWindows.argtypes = [self.callback_type, wintypes.LPARAM]
        for name in ("IsWindowVisible", "IsIconic"):
            getattr(self.user, name).argtypes = [wintypes.HWND]
        self.user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        self.user.MonitorFromWindow.restype = wintypes.HMONITOR
        self.user.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.c_void_p]
        self.style = self.user.GetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else self.user.GetWindowLongW
        self.style.argtypes = [wintypes.HWND, ctypes.c_int]
        self.style.restype = ctypes.c_ssize_t
        self.dwm.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]

    def windows(self, screens):
        class MonitorInfo(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                        ("work", wintypes.RECT), ("flags", wintypes.DWORD),
                        ("device", wintypes.WCHAR * 32)]

        result = []

        @self.callback_type
        def visit(handle, _):
            pid = wintypes.DWORD()
            self.user.GetWindowThreadProcessId(handle, ctypes.byref(pid))
            if pid.value == os.getpid() or not self.user.IsWindowVisible(handle) or self.user.IsIconic(handle):
                return True
            cloaked = wintypes.DWORD()
            self.dwm.DwmGetWindowAttribute(handle, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
            if cloaked.value:
                return True
            name = ctypes.create_unicode_buffer(256)
            self.user.GetClassNameW(handle, name, 256)
            if name.value in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
                return True
            rect = wintypes.RECT()
            if self.dwm.DwmGetWindowAttribute(handle, 9, ctypes.byref(rect), ctypes.sizeof(rect)) != 0:
                if not self.user.GetWindowRect(handle, ctypes.byref(rect)):
                    return True
            info = MonitorInfo()
            info.size = ctypes.sizeof(info)
            monitor = self.user.MonitorFromWindow(handle, 2)
            if not self.user.GetMonitorInfoW(monitor, ctypes.byref(info)):
                return True
            # Qt 6 can expose the friendly monitor name instead of \\.\DISPLAYn.
            # On Windows Qt keeps native monitor origins, scaling only sizes.
            screen = next((s for s in screens if s.name() == info.device or
                           (s.geometry().x() == info.monitor.left and
                            s.geometry().y() == info.monitor.top)), None)
            if screen is None:
                return True
            geometry = screen.geometry()
            bounds = logical_rect((rect.left, rect.top, rect.right, rect.bottom),
                                  (info.monitor.left, info.monitor.top),
                                  (geometry.x(), geometry.y()), screen.devicePixelRatio())
            if bounds[2] > bounds[0] and bounds[3] > bounds[1]:
                result.append(WindowInfo(int(handle), bounds, not bool(self.style(handle, -20) & 0x80)))
            return True

        self.user.EnumWindows(visit, 0)
        return result

"""Keep Qt's Windows ICU dependency consistent in PyInstaller probe processes."""
import os
from pathlib import Path
import sys

from PyInstaller import isolated
from PyInstaller.__main__ import run


def preload_windows_icu():
    import ctypes
    import os
    ctypes.WinDLL(os.path.join(os.environ["SystemRoot"], "System32", "icuuc.dll"))


if __name__ == "__main__":
    preload_windows_icu()
    # External tools (notably Poppler/Conda) can provide incompatible ICU exports.
    # The application already preloads Windows ICU; do the same in each build
    # probe without modifying PyInstaller or the installed Python environment.
    original_enter = isolated.Python.__enter__

    def enter_with_icu(self):
        result = original_enter(self)
        self.call(preload_windows_icu)
        return result

    isolated.Python.__enter__ = enter_with_icu
    system = Path(os.environ["SystemRoot"])
    os.environ["PATH"] = os.pathsep.join([
        str(system / "System32"), str(system), str(Path(sys.executable).parent),
        str(Path(sys.base_prefix) / "Library" / "bin"),
    ])
    run(sys.argv[1:])

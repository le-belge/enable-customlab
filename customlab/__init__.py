"""e-NABLE CustomLab — core library (no GUI yet)."""
import os as _os
import sys as _sys

__version__ = "0.1.0"


def windows_offscreen_fonts():
    """On Windows, Qt's offscreen platform (tests, command line, --selftest) does not look in C:\\Windows\\Fonts and draws every
    letter as an empty box. Point it there. Must run before the QApplication is created; does nothing elsewhere."""
    if _sys.platform == "win32" and _os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        _os.environ.setdefault("QT_QPA_FONTDIR", _os.path.join(_os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))


windows_offscreen_fonts()        # covers a QApplication created by the caller right after importing customlab

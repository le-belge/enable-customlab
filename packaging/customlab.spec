# PyInstaller spec (macOS .app and Windows folder). Run from the project root: see packaging/build_mac.sh / build_windows.bat.
# Bundled: code, profiles, assets, the 16 Phoenix parts (customlab/bundled_parts, with their licences), the tutorial, one example SVG.
# NOT bundled: the user's SCAD/STL sources, OpenSCAD, the 'experiments', 'outputs', 'user_assets' and 'validation_pack' folders.
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
VERSION = "0.9.0-test"
datas = [(str(ROOT / "customlab" / "assets"), "customlab/assets"), (str(ROOT / "customlab" / "profiles"), "customlab/profiles"),
         (str(ROOT / "customlab" / "bundled_parts"), "customlab/bundled_parts"), (str(ROOT / "docs" / "TUTO_ECHELLES.md"), "docs"),
         (str(ROOT / "examples" / "star.svg"), "examples")]
excludes = ["tkinter", "unittest", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtPdf"]

a = Analysis([str(ROOT / "packaging" / "entry.py")], pathex=[str(ROOT)], datas=datas, hiddenimports=["PySide6.QtSvg", "PySide6.QtSvgWidgets", "PySide6.QtOpenGLWidgets"], excludes=excludes)
pyz = PYZ(a.pure)
icon = str(ROOT / "packaging" / ("CustomLab.icns" if sys.platform == "darwin" else "CustomLab.ico"))
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="CustomLab", console=False, icon=icon)
coll = COLLECT(exe, a.binaries, a.datas, name="CustomLab")
if sys.platform == "darwin":
    app = BUNDLE(coll, name="e-NABLE CustomLab.app", icon=icon, bundle_identifier="fr.enable.customlab.test", version=VERSION,
                 info_plist={"CFBundleDisplayName": "e-NABLE CustomLab", "NSHighResolutionCapable": True, "LSMinimumSystemVersion": "11.0"})

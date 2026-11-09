#!/bin/bash
# Builds "e-NableLab.app" (macOS) into dist/. Needs the project's .venv with PySide6, numpy and pyinstaller.
set -e
cd "$(dirname "$0")/.."
.venv/bin/python -m PyInstaller packaging/customlab.spec --noconfirm --distpath dist --workpath build
codesign --force --deep --sign - "dist/e-NableLab.app"        # ad-hoc signature (no Apple developer account): testers open it with right-click > Open
cd dist && rm -f "e-NableLab_mac.zip" && ditto -c -k --sequesterRsrc --keepParent "e-NableLab.app" "e-NableLab_mac.zip"
echo "OK : dist/e-NableLab_mac.zip"

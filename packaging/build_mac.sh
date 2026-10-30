#!/bin/bash
# Builds "e-NABLE CustomLab.app" (macOS) into dist/. Needs the project's .venv with PySide6, numpy and pyinstaller.
set -e
cd "$(dirname "$0")/.."
.venv/bin/python -m PyInstaller packaging/customlab.spec --noconfirm --distpath dist --workpath build
codesign --force --deep --sign - "dist/e-NABLE CustomLab.app"        # ad-hoc signature (no Apple developer account): testers open it with right-click > Open
cd dist && rm -f "e-NABLE_CustomLab_mac.zip" && ditto -c -k --sequesterRsrc --keepParent "e-NABLE CustomLab.app" "e-NABLE_CustomLab_mac.zip"
echo "OK : dist/e-NABLE_CustomLab_mac.zip"

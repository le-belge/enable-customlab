@echo off
REM Builds the Windows version into dist\e-NableLab\ (run on a Windows PC, from this folder or anywhere).
REM Needs Python 3.9+ : py -3 -m venv .venv  then  .venv\Scripts\python -m pip install "PySide6-Essentials<6.12" numpy pyinstaller
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (echo Environnement .venv introuvable : voir packaging\LISEZ-MOI_BUILD.md & exit /b 1)
.venv\Scripts\python -m PyInstaller packaging\customlab.spec --noconfirm --distpath dist --workpath build || exit /b 1
powershell -NoProfile -Command "Compress-Archive -Path 'dist\e-NableLab' -DestinationPath 'dist\e-NableLab_windows.zip' -Force"
echo OK : dist\e-NableLab_windows.zip

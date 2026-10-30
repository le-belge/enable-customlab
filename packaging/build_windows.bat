@echo off
REM Builds the Windows version into dist\CustomLab\ (run on a Windows PC, from this folder or anywhere).
REM Needs Python 3.9+ : py -3 -m venv .venv  then  .venv\Scripts\python -m pip install PySide6-Essentials numpy pyinstaller
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (echo Environnement .venv introuvable : voir packaging\LISEZ-MOI_BUILD.md & exit /b 1)
.venv\Scripts\python -m PyInstaller packaging\customlab.spec --noconfirm --distpath dist --workpath build || exit /b 1
powershell -NoProfile -Command "Compress-Archive -Path 'dist\CustomLab' -DestinationPath 'dist\e-NABLE_CustomLab_windows.zip' -Force"
echo OK : dist\e-NABLE_CustomLab_windows.zip

@echo off
rem Double-cliquez pour lancer e-NABLE CustomLab (Windows).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Environnement .venv introuvable : voir README.md
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m customlab.gui

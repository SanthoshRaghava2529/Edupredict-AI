@echo off
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -m tkinter_app.main
) else (
    python -m tkinter_app.main
)
pause

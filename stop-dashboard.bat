@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" exit /b 0
".venv\Scripts\python.exe" "scripts\launcher.py" --stop
if errorlevel 1 pause

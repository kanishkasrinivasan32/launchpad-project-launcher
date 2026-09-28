@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 goto missing_python
where node >nul 2>&1
if errorlevel 1 goto missing_node
if not exist ".venv\Scripts\python.exe" (
    echo Creating Python environment...
    python -m venv .venv
    if errorlevel 1 goto failed
)
if not exist ".venv\launcher-deps.ready" (
    echo Installing backend dependencies...
    ".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
    if errorlevel 1 goto failed
    type nul > ".venv\launcher-deps.ready"
)
if not exist "frontend\node_modules\.package-lock.json" (
    echo Installing frontend dependencies...
    pushd frontend
    call npm.cmd ci
    if errorlevel 1 (
        popd
        goto failed
    )
    popd
)
if not exist ".env" copy /y ".env.example" ".env" >nul
echo Starting Launchpad. Your browser will open when it is ready.
start "" /b ".venv\Scripts\pythonw.exe" "scripts\launcher.py"
exit /b 0
:missing_python
echo Python 3.11 or newer is required. Install Python and enable "Add Python to PATH".
goto failed
:missing_node
echo Node.js 22.12 or newer is required. Install Node.js LTS and reopen this launcher.
:failed
echo Launch failed. See the message above.
pause
exit /b 1

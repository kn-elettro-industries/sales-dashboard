@echo off
title Sales Intelligence Dashboard
echo ========================================================
echo   🚀 STARTING SALES INTELLIGENCE DASHBOARD
echo   (Type Ctrl+C to Stop)
echo ========================================================
echo.

cd /d "%~dp0"

:: 0. Check Environment
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo.
    echo Please double-click 'Setup_App.bat' first to install dependencies.
    echo.
    pause
    exit /b
)

:: 1. Start the Watcher in background
echo [INFO] Starting Automation Service (Watcher)...
start /B .venv\Scripts\python.exe watcher.py > nul 2>&1

:: 2. Start the Dashboard
echo [INFO] Launching Dashboard Interface...
echo.
.venv\Scripts\python.exe -m streamlit run app.py --server.address 0.0.0.0 --server.headless true

pause

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

:: 1. Start the FastAPI Backend Service (in background)
echo [INFO] Starting Backend API Service (FastAPI) on port 8000...
start /B .venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --log-level warning

:: Wait for API to warm up
ping 127.0.0.1 -n 4 > nul

:: 2. Start the Dashboard
echo [INFO] Launching Dashboard Interface...
echo.
.venv\Scripts\python.exe -m streamlit run app.py --server.address 0.0.0.0

pause

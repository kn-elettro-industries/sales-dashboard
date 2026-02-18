@echo off
titulo Sales Dashboard Setup
echo ========================================================
echo   🛠️  SETTING UP SALES DASHBOARD ENVIRONMENT
echo ========================================================
echo.

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.9+ and try again.
    pause
    exit /b
)

:: 2. Create Virtual Environment
if not exist ".venv" (
    echo [INFO] Creating virtual environment (.venv)...
    python -m venv .venv
) else (
    echo [INFO] Virtual environment already exists.
)

:: 3. Install Dependencies
echo [INFO] Installing required libraries...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

:: 4. Create Directory Structure
echo [INFO] Ensuring data directories exist...
if not exist "data\raw" mkdir "data\raw"
if not exist "data\processed" mkdir "data\processed"
if not exist "data\output" mkdir "data\output"

echo.
echo ========================================================
echo   ✅ SETUP COMPLETE!
echo   You can now double-click 'Run_App.bat' to start.
echo ========================================================
pause

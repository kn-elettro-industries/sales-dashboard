@echo off
title Push Sales Dashboard to GitHub
echo ========================================================
echo   🚀 PUSHING SALES DASHBOARD TO GITHUB
echo ========================================================
echo.
echo NOTE: Make sure you are logged into GitHub!
echo Repository: https://github.com/Commanderadi/sales-dashboard.git
echo.
pause

cd /d "%~dp0"

:: 0. Configure Git Identity (Local Repo)
:: We forcefully set it for this repo to avoid "Author identity unknown" errors.
git config user.name "Elettro Admin"
git config user.email "admin@elettro.com"

:: 1. Initialize Git
if not exist ".git" (
    echo [INFO] Initializing Git repository...
    git init
) else (
    echo [INFO] Git repository already optimized.
)

:: 2. Add Remote Origin (Force update if exists)
echo [INFO] Setting remote origin...
git remote remove origin >nul 2>&1
git remote add origin https://github.com/Commanderadi/sales-dashboard.git

:: 3. Add Files & Commit
echo [INFO] Staging files...
git add .
:: Force add the master file in case it was ignored
git add -f data/masters/customer_master.xlsx
echo [INFO] Committing changes...
git commit -m "Auto-Deploy: Initial Setup"

:: 4. Push to Main
echo [INFO] Renaming branch to 'main'...
git branch -M main

echo.
echo [INFO] Pushing to GitHub (Forcing overwrite)...
echo (If prompted, please enter your GitHub username/password/token)
echo.
git push -u origin main --force

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Push failed! Please check your credentials or internet.
    pause
    exit /b
)

echo.
echo ========================================================
echo   ✅ SUCCESS! CODE IS NOW ON GITHUB.
echo ========================================================
echo Next Step: Go to https://share.streamlit.io/ to deploy!
pause

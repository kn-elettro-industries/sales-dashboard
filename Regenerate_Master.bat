@echo off
echo --- Regenerating Sales Master Excel ---
echo.
echo NOTE: Please ensure 'data/output/sales_master.xlsx' is CLOSED before running this.
echo.
".venv\Scripts\python.exe" scripts\regenerate_excel.py
echo.
pause

@echo off
title AI Data Analyst Assistant - Dashboard Server
color 0A

echo.
echo ========================================
echo AI Data Analyst Assistant
echo ========================================
echo.
echo Activating virtual environment...
cd /d "c:\Users\VICTUS\OneDrive\Desktop\AI-Data-analyst and assistant"
call .venv\Scripts\activate.bat

echo Starting Flask server...
echo.
echo Server will be available at: http://localhost:5000/dashboard
echo Press CTRL+C to stop the server
echo.

python backend\app.py

pause

@echo off
title AI Data Analyst Assistant - Dashboard Server
color 0A

echo.
echo ========================================
echo AI Data Analyst Assistant
echo ========================================
echo.
cd /d "c:\Users\VICTUS\OneDrive\Desktop\AI-Data-analyst and assistant"
set PYTHON_EXE=%CD%\.venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
  echo Could not find virtual environment Python at:
  echo %PYTHON_EXE%
  echo.
  echo Run this once:
  echo python -m venv .venv
  echo .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)

echo Starting Flask server...
echo.
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /R /C:"IPv4 Address"') do (
  if not defined LAN_IP set LAN_IP=%%i
)
if defined LAN_IP set LAN_IP=%LAN_IP: =%

echo Server will be available on this computer at: http://localhost:5000/dashboard
if defined LAN_IP (
  echo Use this link on another device on the same Wi-Fi/network:
  echo http://%LAN_IP%:5000/dashboard
) else (
  echo Could not detect a network IP. Run ipconfig and use your IPv4 address:
  echo http://YOUR_IPV4_ADDRESS:5000/dashboard
)
echo Press CTRL+C to stop the server
echo.

"%PYTHON_EXE%" backend\app.py

pause

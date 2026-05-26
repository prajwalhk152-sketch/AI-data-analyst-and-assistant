@echo off
title AI Data Analyst Assistant - Streamlit
color 0A

echo.
echo ========================================
echo AI Data Analyst Assistant - Streamlit
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

for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /R /C:"IPv4 Address"') do (
  if not defined LAN_IP set LAN_IP=%%i
)
if defined LAN_IP set LAN_IP=%LAN_IP: =%

echo Starting Streamlit...
echo.
echo App will be available on this computer at: http://localhost:8501
if defined LAN_IP (
  echo Use this link on another device on the same Wi-Fi/network:
  echo http://%LAN_IP%:8501
) else (
  echo Could not detect a network IP. Run ipconfig and use your IPv4 address:
  echo http://YOUR_IPV4_ADDRESS:8501
)
echo.
echo For public internet access, deploy this repo to Streamlit Community Cloud.
echo Press CTRL+C to stop the server
echo.

"%PYTHON_EXE%" -m streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true

pause

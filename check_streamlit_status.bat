@echo off
title Streamlit Status Check
color 0E

echo.
echo Checking Streamlit on port 8501...
echo.

netstat -ano | findstr :8501
if errorlevel 1 (
  echo.
  echo Streamlit is NOT running on port 8501.
  echo Start it by double-clicking run_streamlit.bat and keep that window open.
  echo.
) else (
  echo.
  echo Streamlit appears to be running.
  echo Local link: http://localhost:8501
  for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /R /C:"IPv4 Address"') do (
    if not defined LAN_IP set LAN_IP=%%i
  )
  if defined LAN_IP set LAN_IP=%LAN_IP: =%
  if defined LAN_IP echo Network link: http://%LAN_IP%:8501
  echo.
)

pause

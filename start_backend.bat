@echo off
title Enterprise Multi-Agent Backend
color 0A
echo.
echo  ==========================================
echo   Enterprise Multi-Agent Platform
echo   Backend Server Starting...
echo  ==========================================
echo.

cd /d "c:\Users\RaviMakwana\Downloads\enterprise-multi-agent"

:: Kill any existing process on port 8001
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8001" ^| find "LISTENING" 2^>nul') do (
    echo Stopping existing process on port 8001 (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)

echo Starting backend on http://0.0.0.0:8001
echo Press Ctrl+C to stop the server.
echo.

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload

pause

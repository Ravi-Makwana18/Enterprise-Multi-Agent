@echo off
title Enterprise Multi-Agent Platform - Full Stack
echo.
echo  ==========================================
echo   Starting Full Stack (Backend + Frontend)
echo  ==========================================
echo.

cd /d "c:\Users\RaviMakwana\Downloads\enterprise-multi-agent"

:: Kill anything on port 8001
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8001" ^| find "LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)

:: Start backend in a new window
start "Backend - Port 8001" cmd /k "cd /d c:\Users\RaviMakwana\Downloads\enterprise-multi-agent && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload"

:: Wait 3 seconds for backend to start
timeout /t 3 /nobreak >nul

:: Start frontend in a new window
start "Frontend - Port 5173" cmd /k "cd /d c:\Users\RaviMakwana\Downloads\enterprise-multi-agent\frontend && npm run dev"

echo.
echo  Both servers are starting in separate windows.
echo.
echo  Backend:  http://localhost:8001
echo  Frontend: http://localhost:5173
echo.
echo  Access from network: http://192.168.1.18:5173
echo.
timeout /t 5 /nobreak >nul
start http://localhost:5173

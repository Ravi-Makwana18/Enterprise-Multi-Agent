@echo off
title Enterprise Multi-Agent Frontend
color 0B
echo.
echo  ==========================================
echo   Enterprise Multi-Agent Platform
echo   Frontend Dev Server Starting...
echo  ==========================================
echo.

cd /d "c:\Users\RaviMakwana\Downloads\enterprise-multi-agent\frontend"

echo Starting frontend on http://localhost:5173
echo Press Ctrl+C to stop the server.
echo.

npm run dev

pause

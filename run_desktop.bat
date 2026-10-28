@echo off
title Meikova Harvest Dev
taskkill /f /im electron.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :18650 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
cd /d "%~dp0\electron"
echo Starting Meikova Harvest Desktop App in DEV Mode...
call npm run dev
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with error code %errorlevel%
    pause
)

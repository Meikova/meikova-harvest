@echo off
title EveryThingDownloader Dev
taskkill /f /im electron.exe >nul 2>&1
cd /d "%~dp0\electron"
echo Starting EveryThingDownloader Desktop App in DEV Mode...
call npm run dev
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with error code %errorlevel%
    pause
)

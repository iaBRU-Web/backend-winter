@echo off
title Winter AI - Backend
cd /d "%~dp0"

echo ============================================
echo   Winter AI Backend - starting up...
echo ============================================

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python was not found. Please install Python 3.10+ from https://python.org
    echo then double-click this file again.
    pause
    exit /b 1
)

python -m pip install --quiet --disable-pip-version-check -r requirements.txt

echo.
echo Starting Winter AI on http://localhost:10000
echo Swagger docs available at http://localhost:10000/docs
echo Press CTRL+C in this window to stop the server.
echo.

start "" http://localhost:10000/docs
python -m uvicorn api.index:app --host 0.0.0.0 --port 10000

pause

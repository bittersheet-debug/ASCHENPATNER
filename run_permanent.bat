@echo off
setlocal enabledelayedexpansion
title MEDIAPATNER BOT - PERMANENT WATCHDOG RUNNER

:: Navigasi ke direktori script
cd /d "%~dp0"

:: Pastikan folder data ada
if not exist "data" mkdir data

echo ======================================================================
echo    MEDIAPATNER BOT - ASCHEN EVENT ORGANIZER
echo    Permanent Watchdog Runner (Auto-Restart on Crash)
echo ======================================================================
echo.

:: Cari Python yang sesuai
set "PY_CMD="
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else (
    where python >nul 2>nul
    if !errorlevel! equ 0 (
        set "PY_CMD=python"
    ) else (
        echo [ERROR] Python tidak ditemukan di sistem!
        echo Pastikan Python 3.10+ sudah terinstall.
        pause
        exit /b 1
    )
)

echo [INFO] Menggunakan Python: !PY_CMD!
echo [INFO] Memulai loop auto-restart permanen...
echo [INFO] Log dicatat ke: data\bot_runtime.log
echo.

:LOOP
echo [%date% %time%] [WATCHDOG] Memulai MEDIAPATNER BOT... >> data\bot_runtime.log
echo [%date% %time%] [WATCHDOG] Bot dimulai.

"!PY_CMD!" -u main.py >> data\bot_runtime.log 2>&1

set EXIT_CODE=%errorlevel%
echo [%date% %time%] [WATCHDOG] Bot terhenti dengan kode keluar: %EXIT_CODE% >> data\bot_runtime.log
echo [WARNING] Bot terhenti (Exit Code: %EXIT_CODE%). Melakukan restart otomatis dalam 3 detik...

timeout /t 3 /nobreak >nul
goto LOOP
